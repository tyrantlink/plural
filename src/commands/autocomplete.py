from discord import AutocompleteContext
from thefuzz import process  # type: ignore
from src.db import Group


async def groups(ctx: AutocompleteContext) -> list[str]:
    if ctx.interaction.user is None:
        return ['you do not exist']

    groups = [group.name for group in await Group.find({'accounts': ctx.interaction.user.id}).to_list()]

    if not groups:
        return ['no groups found, run /manage to create one']

    if ctx.value == '':
        return groups[:25]

    processed_groups = process.extract(ctx.value, groups, limit=5)
    process_failed = all(g[1] == 0 for g in processed_groups)

    return [
        group[0]
        for group in
        processed_groups
        if group[1] > 60 or process_failed
    ] or [
        'no groups matched, run /manage to create a new one'
    ]


async def members(ctx: AutocompleteContext) -> list[str]:
    if ctx.interaction.user is None:
        return ['you do not exist']

    groups = await Group.find({'accounts': ctx.interaction.user.id}).to_list()

    selected_group = next(
        (  # ? select group based on option
            group
            for group in
            groups
            if group.name == ctx.options.get('group')
        ),
        None
    ) or next(
        (  # ? or select the default
            group
            for group in groups
            if group.name == 'default'
        ),
        None
    )

    if selected_group is None:
        return ['no group selected']

    members = [member.name for member in await selected_group.get_members()]

    if not members:
        return ['no members found, run /manage to create one']

    if ctx.value == '':
        return members[:25]

    processed_members = process.extract(ctx.value, members, limit=5)
    process_failed = all(m[1] == 0 for m in processed_members)

    return [
        member[0]
        for member in
        processed_members
        if member[1] > 60 or process_failed
    ] or [
        'no members matched, run /manage to create a new one'
    ]
