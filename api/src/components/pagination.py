from enum import Enum

from beanie import PydanticObjectId

from plural.db import Usergroup, Group, ProxyMember
from plural.db.enums import PaginationStyle
from plural.errors import InteractionError

from src.core.emoji import EMOJI

from src.discord import (
    ButtonStyle,
    Interaction,
    ActionRow,
    button,
    Embed,
    Emoji
)

from .base import _send_or_update


__all__ = (
    'PAGES',
)


PAGES = {
    'pagination': lambda interaction, category, group_id: _pagination(
        interaction, category, group_id=group_id)
}

PAGINATION_STYLE_MAP: dict[PaginationStyle, tuple[str, str] | tuple[Emoji, Emoji]] = {
    PaginationStyle.BASIC_ARROWS: ('⬅️', '➡️'),
    PaginationStyle.REM_AND_RAM: (
        EMOJI.get('rem_left', '⬅️'), EMOJI.get('ram_right', '➡️')),
    PaginationStyle.TEXT_ARROWS: ('<-', '->')
}


class SortOrder(Enum):
    ALPHA_ASC = 0
    ALPHA_DESC = 1
    DATE_ASC = 2
    DATE_DESC = 3

    @property
    def type(self) -> str:
        return self.name.split('_')[0].lower()

    @property
    def reverse(self) -> bool:
        return bool(self.value % 2)

    @property
    def description(self) -> str:
        return [
            'Sorting Alphabetically, Ascending',
            'Sorting Alphabetically, Descending',
            'Sorting by Creation Date, Ascending',
            'Sorting by Creation Date, Descending'
        ][self.value]


@button(
    custom_id='button_pagination_left',
    label='⬅️',
    style=ButtonStyle.SECONDARY)
async def button_pagination_left(
    interaction: Interaction,
    category: str,
    page: int = 0,
    sort: int = 0,
    group_id: str | None = None
) -> None:
    await _pagination(
        interaction,
        category,
        page - 1,
        SortOrder(sort),
        PydanticObjectId(group_id) if group_id else None
    )


@button(
    custom_id='button_pagination_right',
    label='➡️',
    style=ButtonStyle.SECONDARY)
async def button_pagination_right(
    interaction: Interaction,
    category: str,
    page: int = 0,
    sort: int = 0,
    group_id: str | None = None
) -> None:
    await _pagination(
        interaction,
        category,
        page + 1,
        SortOrder(sort),
        PydanticObjectId(group_id) if group_id else None
    )


@button(
    custom_id='button_pagination_sort',
    label='Change Sort Type',
    style=ButtonStyle.SECONDARY)
async def button_pagination_sort(
    interaction: Interaction,
    category: str,
    page: int = 0,
    sort: int = 0,
    group_id: str | None = None
) -> None:
    await _pagination(
        interaction,
        category,
        page,
        SortOrder((sort + 1) % len(SortOrder)),
        PydanticObjectId(group_id) if group_id else None
    )


def _format_values(
    values: list[ProxyMember | Group],
    start: int = 0
) -> list[str]:
    padding = len(str(start + len(values))) + 3

    def padded(index: int) -> str:
        return f'`{index}`'.ljust(
            padding
        ).replace(
            ' ', ' ​'
        ).strip('​')

    match values[0]:
        case Group():
            return [
                f'{padded(index)}**{group.name}**' +
                (f'`{group.tag}`' if group.tag else '') +
                f' ({len(group.members)} member' +
                ('s' if len(group.members) != 1 else '') + ')'
                for index, group in enumerate(values, start + 1)]
        case ProxyMember():
            return [
                f'{padded(index)}**{member.name}**' + (
                    f' ({', '.join(tag.name for tag in member.proxy_tags)})'
                    if member.proxy_tags else '')
                for index, member in enumerate(values, start + 1)
            ]


async def _pagination(
    interaction: Interaction,
    category: str,
    page: int = 0,
    sort: SortOrder = SortOrder.ALPHA_ASC,
    group_id: PydanticObjectId | None = None
) -> None:
    usergroup = await Usergroup.get_by_user(interaction.author_id)

    left, right = PAGINATION_STYLE_MAP[usergroup.config.pagination_style]

    match left, right:
        case Emoji(), Emoji():
            button_left = button_pagination_left.with_overrides(
                label='', emoji=left)
            button_right = button_pagination_right.with_overrides(
                label='', emoji=right)
        case str(), str():
            button_left = button_pagination_left.with_overrides(
                label=left)
            button_right = button_pagination_right.with_overrides(
                label=right)
        case _:
            raise InteractionError('Invalid pagination style')

    groups = (
        [await Group.get(group_id)]
        if group_id else
        await Group.find({
            '$or': [
                {'accounts': usergroup.id},
                {f'users.{interaction.author_id}': {'$exists': True}}]
        }).to_list()
    )

    match category:
        case 'group':
            values = groups
        case 'member':
            values = await ProxyMember.find({
                '_id': {'$in': [
                    member_id
                    for group in groups
                    for member_id in group.members]}
            }).to_list()
        case _:
            raise InteractionError('Invalid category')

    match sort.type:
        case 'alpha':
            values.sort(key=lambda x: x.name.lower(), reverse=sort.reverse)
        case 'date':
            values.sort(key=lambda x: str(x.id), reverse=sort.reverse)

    total_pages = (len(values) + 10 - 1) // 10

    if page < 0:
        page += total_pages

    if page >= total_pages:
        page = 0

    page = max(0, min(page, total_pages - 1))

    start_index = page * 10

    formatted_values = (
        _format_values(values[
            start_index:start_index+10],
            start=start_index)
        if values else
        [(
            f'You have no {category}s' +
            (' in this group' if group_id else '')
        )]
    )

    extra = [
        category,
        page,
        sort.value,
        str(group_id) if group_id else None
    ]

    await _send_or_update(
        interaction,
        embed=Embed(
            title=f'{category.capitalize()} List',
            description='\n'.join(formatted_values),
            color=0x69ff69
        ).set_footer(text=(
            (f'Group: {groups[0].name}\n' if group_id else '') + (
                f'Page {page + 1}/{total_pages} | {sort.description}'
                if values else ''
            ))),
        components=[
            ActionRow(components=[
                button_left.with_overrides(
                    disabled=len(values) <= 10,
                    extra=extra),
                button_right.with_overrides(
                    disabled=len(values) <= 10,
                    extra=extra)]),
            ActionRow(components=[
                button_pagination_sort.with_overrides(
                    extra=extra)])
        ] if len(values) > 1 else []
    )
