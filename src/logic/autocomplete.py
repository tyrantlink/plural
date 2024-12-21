from src.discord import Interaction, ApplicationCommandInteractionData, ApplicationCommandOptionType, ApplicationCommandInteractionDataOption, ApplicationCommandOptionChoice
from src.db import ProxyMember, Group, UserConfig
from typing import NamedTuple, Protocol
from thefuzz.utils import full_process
from collections.abc import Callable
from beanie import PydanticObjectId
from bson.errors import InvalidId
from thefuzz import process


class AutocompleteCallback(Protocol):
    async def __call__(
        self,
        interaction: Interaction,
        *args,  # noqa: ANN002
        **kwargs  # noqa: ANN003
) -> list[ApplicationCommandOptionChoice]:
        ...


class ProcessedMember(NamedTuple):
    name: str
    score: int
    member: ProxyMember
    group: Group


__callbacks: dict[str, AutocompleteCallback] = {}


def autocomplete(option_name: str) -> Callable[[AutocompleteCallback], AutocompleteCallback]:
    def decorator(func: AutocompleteCallback) -> AutocompleteCallback:
        if option_name in __callbacks:
            raise ValueError(f'listener for {option_name} already exists')

        __callbacks[option_name] = func
        return func

    return decorator


async def on_autocomplete(interaction: Interaction) -> None:
    assert isinstance(interaction.data, ApplicationCommandInteractionData)

    options = interaction.data.options or []
    focused_option = None

    while focused_option is None:
        for option in options:
            match option.type:
                case ApplicationCommandOptionType.SUB_COMMAND | ApplicationCommandOptionType.SUB_COMMAND_GROUP:
                    options = option.options or []
                    break
                case _ if option.focused is True:
                    focused_option = option
                    break
        else:
            await interaction.response.send_autocomplete_result([])
            return

    callback = __callbacks.get(focused_option.name)

    choices = []
    if callback is not None:
        choices = await callback(
            interaction,
            {
                option.name: option
                for option in options
            }
        )

    await interaction.response.send_autocomplete_result(
        choices
    )


@autocomplete('member')
async def autocomplete_member(
    interaction: Interaction,
    options: dict[str, ApplicationCommandInteractionDataOption],
    userproxies_only: bool = False
) -> list[ApplicationCommandOptionChoice]:
    if options['userproxy' if userproxies_only else 'member'] is None:
        return []

    groups = {
        group.name: group
        for group in
        await Group.find({'accounts': interaction.author_id}).to_list()
    }

    selected_group = options.get('group')

    members: list[tuple[ProxyMember, Group]] = []

    for group in groups.values():
        if selected_group is not None and group.name != selected_group.value:
            continue

        members.extend(
            (member, group)
            for member in
            await group.get_members()
            if not userproxies_only or member.userproxy is not None
        )

    async def return_members(
        members: list[tuple[ProxyMember, Group]]
    ) -> list[ApplicationCommandOptionChoice]:
        # ? check config, always hide if only one group
        hide_groups = ((
            not (
                await UserConfig.get(interaction.author_id) or UserConfig.default()
            ).groups_in_autocomplete
        ) or len(groups) == 1)

        return [
            ApplicationCommandOptionChoice(
                name=f'[{group.name}] {member.name}'[
                    (len(group.name) + 3) if hide_groups else 0:],
                value=str(member.id))
            for member, group in members[:25]
        ]

    if not members:
        return await return_members(members)

    typed_value = str(
        options['userproxy' if userproxies_only else 'member'].value)

    if not full_process(typed_value):
        return await return_members(members)

    return await return_members([
        (member, group)
        for _, score, member, group in [
            ProcessedMember(
                processed[0],
                processed[1],
                processed[2][0],
                processed[2][1]
            )
            for processed in
            process.extract(
                typed_value,
                {
                    (member, group): member.name
                    for member, group in members
                },
                limit=10
            )
        ]
        if score > 60
    ])


@autocomplete('group')
async def autocomplete_group(
    interaction: Interaction,
    options: dict[str, ApplicationCommandInteractionDataOption]
) -> list[ApplicationCommandOptionChoice]:
    groups = {
        group: group.name
        for group in
        await Group.find({'accounts': interaction.author_id}).to_list()
    }

    typed_value = str(options['group'].value)

    if not full_process(typed_value):
        return [
            ApplicationCommandOptionChoice(
                name=group_name,
                value=str(group.id))
            for group, group_name in groups.items()
        ]

    return [
        ApplicationCommandOptionChoice(
            name=processed[0],
            value=str(processed[2].id))
        for processed in
        process.extract(
            typed_value,
            groups,
            limit=10
        )
    ]


@autocomplete('userproxy')
async def autocomplete_userproxy(
    interaction: Interaction,
    options: dict[str, ApplicationCommandInteractionDataOption]
) -> list[ApplicationCommandOptionChoice]:
    return await autocomplete_member(
        interaction,
        options,
        userproxies_only=True
    )


@autocomplete('proxy_tag')
async def autocomplete_proxy_tag(
    interaction: Interaction,  # noqa: ARG001
    options: dict[str, ApplicationCommandInteractionDataOption]
) -> list[ApplicationCommandOptionChoice]:

    member_option = options.get('member')

    if member_option is None:
        return []

    try:
        member_id = PydanticObjectId(str(member_option.value))
    except InvalidId:
        return []

    member = await ProxyMember.get(member_id)

    if member is None:
        return []

    proxy_tags = {
        str(index): f'{tag.prefix}text{tag.suffix}'
        for index, tag in enumerate(member.proxy_tags)
    }

    typed_value = str(options['proxy_tag'].value)

    if not full_process(typed_value):
        return [
            ApplicationCommandOptionChoice(
                name=tag,
                value=index)
            for index, tag in proxy_tags.items()
        ]

    return [
        ApplicationCommandOptionChoice(
            name=processed[0],
            value=str(processed[2]))
        for processed in
        process.extract(
            typed_value,
            proxy_tags,
            limit=15
        )
    ]
