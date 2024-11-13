from src.discord import Interaction, ApplicationCommandInteractionData, ApplicationCommandOptionType, ApplicationCommandInteractionDataOption, ApplicationCommandOptionChoice
from typing import Callable, Awaitable, NamedTuple
from thefuzz.utils import full_process
from src.db import ProxyMember, Group
from thefuzz import process

CallbackType = Callable[
    [
        Interaction,
        dict[str, ApplicationCommandInteractionDataOption]
    ],
    Awaitable[
        list[ApplicationCommandOptionChoice]
    ]
]


class ProcessedMember(NamedTuple):
    name: str
    score: int
    member: ProxyMember
    group: Group


__callbacks: dict[str, CallbackType] = {}


def autocomplete(option_name: str):
    def decorator(
        func: CallbackType
    ):
        if option_name in __callbacks:
            raise ValueError(f'listener for {option_name} already exists')

        __callbacks[option_name] = func
        return func

    return decorator


async def on_autocomplete(interaction: Interaction) -> None:
    assert isinstance(interaction.data, ApplicationCommandInteractionData)
    # from orjson import dumps
    # print('autocomplete', dumps(interaction._raw).decode())

    options = interaction.data.options or []
    focused_option = None

    while focused_option is None:
        for option in options:
            match option.type:
                case ApplicationCommandOptionType.SUB_COMMAND:
                    options = option.options or []
                case ApplicationCommandOptionType.SUB_COMMAND_GROUP:
                    options = option.options or []
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
    options: dict[str, ApplicationCommandInteractionDataOption]
) -> list[ApplicationCommandOptionChoice]:
    if options['member'] is None:
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

        members.extend((
            (member, group)
            for member in
            await group.get_members()
        ))

    def return_members(
        members: list[tuple[ProxyMember, Group]]
    ) -> list[ApplicationCommandOptionChoice]:
        return [
            ApplicationCommandOptionChoice(
                name=f'[{group.name}] {member.name}',
                value=str(member.id)
            )
            for member, group in members[:25]
        ]

    if not members:
        return return_members(members)

    typed_value = str(options['member'].value)

    if not full_process(typed_value):
        return return_members(members)

    return return_members(
        [
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
        ]
    )
