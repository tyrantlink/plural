from discord import AutocompleteContext, OptionChoice
from thefuzz.utils import full_process
from beanie import PydanticObjectId
from src.db import Group, UserProxy
from typing import NamedTuple
from thefuzz import process  # type: ignore


class ProcessedMember(NamedTuple):
    member_id: PydanticObjectId
    member_name: str
    score: int
    group_name: str
    userproxy_id: PydanticObjectId | None = None


async def groups(ctx: AutocompleteContext) -> list[str]:
    assert ctx.interaction.user is not None

    groups = [group.name for group in await Group.find({'accounts': ctx.interaction.user.id}).to_list()]

    if not groups:
        return ['no groups found, run /group new to create one']

    if not full_process(ctx.value):
        return groups[:25]

    processed_groups = process.extract(ctx.value, groups, limit=5)
    process_failed = all(g[1] == 0 for g in processed_groups)

    return [
        group[0]
        for group in
        processed_groups
        if group[1] > 60 or process_failed
    ] or [
        'no groups matched, run /group new to create a new one'
    ]


async def members(ctx: AutocompleteContext) -> list[OptionChoice]:
    assert ctx.interaction.user is not None

    selected_group: str = ctx.options.get('group', None)

    members = [
        (group, member)
        for group in [
            group  # ? restrict to group user has selected
            for group in
            await Group.find({'accounts': ctx.interaction.user.id}).to_list()
            if selected_group in [group.name, None]
        ]
        for member in await group.get_members()
    ]

    if not members:
        return [OptionChoice(name='no members found, run /member new to create one', value='None')]

    if not full_process(ctx.value):
        return [
            OptionChoice(
                name=(
                    ''.join(['{', group.name, '} ', member.name])
                    if selected_group is None
                    else member.name
                ),
                value=str(member.id))
            for group, member in members[:25]
        ]

    processed_members = [
        ProcessedMember(
            processed[2][1],
            processed[0],
            processed[1],
            processed[2][0]
        )
        for processed in
        process.extract(
            ctx.value,
            {
                (group.name, member.id): member.name
                for group, member
                in members
            },
            limit=5
        )
    ]

    process_failed = all(m.score == 0 for m in processed_members)

    return [
        OptionChoice(
            name=(
                ''.join(
                    ['{', processed.group_name, '} ', processed.member_name])
                if selected_group is None
                else processed.member_name
            ),
            value=str(processed.member_id))
        for processed in processed_members
        if processed.score > 60 or process_failed
    ] or [
        OptionChoice(
            name='no members matched, run /member new to create a new one', value='None')
    ]


async def userproxies(ctx: AutocompleteContext) -> list[OptionChoice]:
    assert ctx.interaction.user is not None

    members = [
        (userproxy, await userproxy.get_member())
        for userproxy in [
            userproxy
            for userproxy in
            await UserProxy.find({'user_id': ctx.interaction.user.id}).to_list()
        ]
    ]

    if not userproxies:
        return [OptionChoice(name='no userproxies found, run /userproxy new to create one', value='None')]

    if ctx.value == '' or ctx.value.isspace():
        return [
            OptionChoice(
                name=(
                    ''.join(['{', (await member.get_group()).name, '} ', member.name])
                ),
                value=str(userproxy.id))
            for userproxy, member in members[:25]
        ]

    processed_userproxies = [
        ProcessedMember(
            processed[2][1],
            processed[0],
            processed[1],
            processed[2][0],
            processed[2][2]
        )
        for processed in
        process.extract(
            ctx.value,
            {
                ((await member.get_group()).name, member.id, userproxy.id): member.name
                for userproxy, member
                in members
            },
            limit=5
        )
    ]

    process_failed = all(m.score == 0 for m in processed_userproxies)

    return [
        OptionChoice(
            name=(
                ''.join(
                    ['{', processed.group_name, '} ', processed.member_name])
            ),
            value=str(processed.userproxy_id))
        for processed in processed_userproxies
        if processed.score > 60 or process_failed
    ] or [
        OptionChoice(
            name='no userproxies matched, run /userproxy new to create a new one', value='None')
    ]
