from __future__ import annotations

from typing import NamedTuple, Protocol, TYPE_CHECKING

from thefuzz.utils import full_process
from beanie import PydanticObjectId
from bson.errors import InvalidId
from thefuzz import process

from plural.db import ProxyMember, Group, redis

from src.discord import (
    ApplicationCommandInteractionData,
    ApplicationCommandOptionType,
    ApplicationCommand,
    Interaction
)

if TYPE_CHECKING:
    from collections.abc import Callable


class AutocompleteCallback(Protocol):
    async def __call__(
        self,
        interaction: Interaction,
        *args,  # noqa: ANN002
        **kwargs  # noqa: ANN003
) -> list[ApplicationCommand.Option.Choice]:
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

    choices = [ApplicationCommand.Option.Choice(
        name='autocomplete not implemented',
        value='test'
    )]

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


# ? caching responses saves like, at most 15ms, and rarely comes up
# ? since responses for a single command are cached by the client
# ? but if a user types the same query in two different commands
# ? within 20 seconds, then this will save time
async def cache_check(
    key: str
) -> list[ApplicationCommand.Option.Choice] | None:
    if not (choices := await redis.json().get(key)):
        return None

    return [
        ApplicationCommand.Option.Choice(
            name=choice['name'],
            value=choice['value']
        )
        for choice in choices
    ]


async def cache_add(
    key: str,
    choices: list[ApplicationCommand.Option.Choice]
) -> None:
    pipeline = redis.pipeline()
    await pipeline.json().set(
        key,
        '$',
        [choice.as_payload() for choice in choices])
    await pipeline.expire(key, 15)
    await pipeline.execute()


@autocomplete('member')
async def autocomplete_member(
    interaction: Interaction,
    options: dict[str, ApplicationCommandInteractionData.Option],
    userproxies_only: bool = False
) -> list[ApplicationCommand.Option.Choice]:
    async def return_members(
        members: list[tuple[ProxyMember, Group]],
        sort: bool
    ) -> list[ApplicationCommand.Option.Choice]:
        hide_groups = (len(groups) == 1 or (
            (user := await interaction.get_usergroup())
            and not user.config.groups_in_autocomplete
        ))

        responses = [
            ApplicationCommand.Option.Choice(
                name=(base_name + (
                    f' ({member.meta[:97-len(base_name)]})'
                    if member.meta else
                    ''
                ))[:100],
                value=str(member.id))
            for member, group in members[:25]
            if (
                base_name := (
                    f'[{group.name}] '
                    if not hide_groups else
                    ''
                ) + member.name
            )
        ]

        if sort:
            recent_proxies = dict(await redis.zrange(
                f'recent_proxies:{interaction.author_id}',
                0,
                -1,
                withscores=True
            ))

            responses.sort(
                reverse=True,
                key=lambda choice: (
                    recent_proxies.get(choice.value, 0),
                    choice.name
                )
            )

            if interaction.data.name == 'switch':
                responses.insert(1, ApplicationCommand.Option.Choice(
                    name='Out (Disable Autoproxy)',
                    value='out'))
                responses = responses[:25]

        await cache_add(redis_key, responses)

        return responses

    category = 'userproxy' if userproxies_only else 'member'

    if options.get(category) is None:
        return []

    query = (
        (query := options.get(category))
        and str(query.value)
    )

    redis_key = ':'.join((
        'autocomplete',
        str(interaction.author_id),
        category,
        query or ''
    ))

    if (cached := await cache_check(redis_key)):
        return cached

    usergroup = await interaction.get_usergroup()

    groups = await Group.find({
        '$or': [
            {'account': usergroup.id},
            {f'users.{interaction.author_id}': {'$exists': True}}]
    }).to_list()

    members = [
        (member, group)
        for group in groups
        for member in await group.get_members()
        if not userproxies_only or member.userproxy is not None
    ]

    if not members:
        return []

    if not full_process(query):
        return await return_members(members, sort=True)

    return await return_members([
        (member, group)
        for _, score, member, group in [
            ProcessedMember(
                processed[0],
                processed[1],
                processed[2][0],
                processed[2][1])
            for processed in
            process.extract(
                query,
                {
                    (member, group): member.name
                    for member, group in members
                },
                limit=10)]
        if score > 60
    ], sort=False)


@autocomplete('userproxy')
async def autocomplete_userproxy(
    interaction: Interaction,
    options: dict[str, ApplicationCommandInteractionData.Option]
) -> list[ApplicationCommand.Option.Choice]:
    return await autocomplete_member(
        interaction,
        options,
        userproxies_only=True
    )


@autocomplete('group')
async def autocomplete_group(
    interaction: Interaction,
    options: dict[str, ApplicationCommandInteractionData.Option]
) -> list[ApplicationCommand.Option.Choice]:
    query = (
        (query := options.get('group'))
        and str(query.value)
    )

    redis_key = ':'.join((
        'autocomplete',
        str(interaction.author_id),
        'group',
        query or ''
    ))

    if (cached := await cache_check(redis_key)):
        return cached

    usergroup = await interaction.get_usergroup()

    groups = await Group.find({
        '$or': [
            {'account': usergroup.id},
            {f'users.{interaction.author_id}': {'$exists': True}}]
    }).to_list()

    responses = (
        [
            ApplicationCommand.Option.Choice(
                name=processed[0],
                value=str(processed[2].id))
            for processed in
            process.extract(
                query,
                {
                    group: group.name
                    for group in groups
                },
                limit=10
            )
        ]
        if full_process(query)
        else [
            ApplicationCommand.Option.Choice(
                name=group.name,
                value=str(group.id))
            for group in groups[:25]
        ]
    )

    await cache_add(redis_key, responses)

    return responses


@autocomplete('proxy_tag')
async def autocomplete_proxy_tag(
    interaction: Interaction,
    options: dict[str, ApplicationCommandInteractionData.Option]
) -> list[ApplicationCommand.Option.Choice]:
    member_id = options.get('member')

    if member_id is None:
        return [
            ApplicationCommand.Option.Choice(
                name='Select a member first',
                value='-1'
            )
        ]

    query = (
        (query := options.get('proxy_tag'))
        and str(query.value)
    )

    redis_key = ':'.join((
        'autocomplete',
        str(interaction.author_id),
        'proxy_tag',
        str(member_id.value),
        query or ''
    ))

    if (cached := await cache_check(redis_key)):
        return cached

    try:
        member_id = PydanticObjectId(str(member_id.value))
    except InvalidId:
        return [
            ApplicationCommand.Option.Choice(
                name='Invalid member selected, use the autocomplete',
                value='1'
            )
        ]

    member = await ProxyMember.get(member_id)

    if member is None:
        return [
            ApplicationCommand.Option.Choice(
                name='Member not found',
                value='1'
            )
        ]

    proxy_tags = {
        str(index): f'{tag.prefix}text{tag.suffix}'
        for index, tag in enumerate(member.proxy_tags)
    }

    if not full_process(query):
        responses = [
            ApplicationCommand.Option.Choice(
                name=tag,
                value=index)
            for index, tag in proxy_tags.items()
        ]

        await cache_add(redis_key, responses)

        return responses

    responses = [
        ApplicationCommand.Option.Choice(
            name=processed[0],
            value=str(processed[2]))
        for processed in
        process.extract(
            query,
            proxy_tags,
            limit=10
        )
    ]

    await cache_add(redis_key, responses)

    return responses
