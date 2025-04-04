from textwrap import dedent
from asyncio import gather

from beanie import PydanticObjectId
from pydantic import Field

from plural.db import Usergroup, Group, Message, AutoProxy, ProxyMember, redis
from plural.db.usergroup import AvatarOnlyMember as _AvatarOnlyMember
from plural.errors import PluralExceptionCritical, InteractionError

from src.porting import StandardExport
from src.discord import (
    ButtonStyle,
    Interaction,
    ActionRow,
    button,
    Embed
)

from src.commands.helpers import delete_avatars


__all__ = (
    'PAGES',
)


PAGES = {
    'delete_all_data': lambda interaction: _delete_all_data(interaction),
    'import_confirm': lambda interaction, logs, key: _import_confirm(interaction, logs, key),
    'delete_group': lambda interaction, group: _delete_group(interaction, group),
}


class DeletionMember(_AvatarOnlyMember):
    id: PydanticObjectId = Field(alias='_id')
    userproxy: ProxyMember.UserProxy | None


async def _send_or_update(
    interaction: Interaction,
    embed: Embed,
    components: list[ActionRow]
) -> None:
    if interaction.message:
        if interaction.response.responded:
            await interaction.followup.edit_message(
                interaction.message.id,
                embeds=[embed],
                components=components)
        else:
            await interaction.response.update_message(
                embeds=[embed],
                components=components)
        return

    await interaction.send(
        embeds=[embed],
        components=components
    )


@button(
    custom_id='button_delete_all_data',
    label='Delete All Data',
    style=ButtonStyle.DANGER)
async def button_delete_all_data(interaction: Interaction) -> None:
    await _send_or_update(
        interaction,
        embed=interaction.message.embeds[0],
        components=[
            ActionRow(
                components=[
                    button_delete_confirm
                ]
            )
        ]
    )


@button(
    custom_id='button_delete_confirm',
    label='Press again to confirm',
    style=ButtonStyle.DANGER)
async def button_delete_confirm(interaction: Interaction) -> None:
    from src.commands.userproxy import _delete_userproxy

    db = Usergroup.get_settings().motor_db

    if db is None:
        raise PluralExceptionCritical('Database not connected')

    await interaction.response.update_message(
        components=[
            ActionRow(components=[
                button_delete_confirm.with_overrides(
                    label='Deletion in progress...',
                    disabled=True
                )
            ])
        ]
    )

    tasks = []
    avatars = []

    usergroup = await interaction.get_usergroup()

    groups = await Group.find({
        '$or': [
            {'account': usergroup.id},
            {f'users.{interaction.author_id}': {'$exists': True}}]
    }).to_list()

    member_ids = set()

    for group in groups:
        group.users.pop(interaction.author_id, None)

        if group.avatar:
            avatars.append((group, None))

        tasks.append(group.delete())

        member_ids.update(group.members)

    members = await ProxyMember.find({
        '_id': {'$in': list(member_ids)}
    }, projection_model=DeletionMember).to_list()

    for member in members:
        if member.avatar:
            avatars.append((member, None))

        for index, tag in enumerate(member.proxy_tags):
            if tag.avatar:
                avatars.append((member, index))

    tasks.extend(
        _delete_userproxy(userproxy)
        for userproxy in (
            member
            for member in members
            if member.userproxy
        )
    )

    tasks.append(ProxyMember.find({
        '_id': {'$in': list(member_ids)}
    }).delete_many())

    tasks.append(Message.find({
        'author_id': interaction.author_id
    }).delete_many())

    tasks.append(AutoProxy.find({
        'user': usergroup.id,
    }).delete_many())

    tasks.append(usergroup.delete())

    await delete_avatars(avatars, False)

    await gather(*tasks)

    await interaction.followup.edit_message(
        '@original',
        components=[],
        embeds=[Embed(
            title='Data Deleted',
            description='Your data has been successfully deleted.',
            color=0x69ff69
        )]
    )


@button(
    custom_id='button_import_anyway',
    label='Import Anyway',
    style=ButtonStyle.SECONDARY)
async def button_import_anyway(
    interaction: Interaction,
    key: str
) -> None:
    data = await redis.json().get(
        f'pending_import:{key}'
    )

    if data is None:
        raise InteractionError(
            'Pending import not found. Button must be clicked within 15 minutes of import command'
        )

    export = StandardExport.model_validate(data)

    await interaction.response.update_message(
        components=[
            ActionRow(components=[
                button_import_anyway.with_overrides(
                    label='Import in progress...',
                    disabled=True
                )
            ])
        ]
    )

    logs = await export.do_import(interaction.author_id, False)

    await redis.delete(f'pending_import:{key}')

    log = '\n'.join(logs)

    await interaction.followup.edit_message(
        '@original',
        components=[],
        embeds=[Embed.success(
            title='Import Complete',
            message=(
                '\n'.join([
                    'Import produced the following logs:',
                    '```',
                    log if len(log) < 4040 else f'{log[:4037]}...',
                    '```'])
                if logs else
                'No errors found'
            )
        )]
    )


@button(
    custom_id='button_delete_group',
    label='Delete Group',
    style=ButtonStyle.DANGER)
async def button_delete_group(
    interaction: Interaction,
    group: Group
) -> None:
    from src.commands.userproxy import _delete_userproxy
    from src.commands.group import group_edit_check

    group_edit_check(group, interaction.author_id)

    await interaction.response.update_message(
        components=[
            ActionRow(components=[
                button_delete_group.with_overrides(
                    label='Deletion in progress...',
                    disabled=True
                )
            ])
        ]
    )

    avatars = []

    if group.avatar:
        avatars.append((group, None))

    members = await ProxyMember.find({
        '_id': {'$in': list(group.members)}
    }, projection_model=DeletionMember).to_list()

    await gather(*[
        _delete_userproxy(userproxy)
        for userproxy in (
            member
            for member in members
            if member.userproxy
        )
    ])

    for member in members:
        if member.avatar:
            avatars.append((member, None))

        for index, tag in enumerate(member.proxy_tags):
            if tag.avatar:
                avatars.append((member, index))

    await delete_avatars(avatars, False)

    await ProxyMember.find({
        '_id': {'$in': list(group.members)}
    }).delete_many()

    await group.delete()

    await interaction.followup.edit_message(
        '@original',
        components=[],
        embeds=[Embed.success(
            title='Group Deleted',
            message=(
                f'Group `{group.name}` has been successfully deleted' + (
                    f' alongside {len(members)} members' if members else ''
                )
            )
        )]
    )


async def _delete_all_data(
    interaction: Interaction
) -> None:
    usergroup = await Usergroup.find_one({
        'users': interaction.author_id
    })

    if usergroup is None:
        raise InteractionError('User data not found')

    await _send_or_update(
        interaction,
        embed=Embed(
            title='Delete all data',
            description=dedent(
                """
                Are you sure you want to delete all of your data, including, but not limited to, all groups, members, and avatars?

                This action is irreversible.
                """
            ).strip(),
            color=0xff6969
        ).set_footer(
            text='Click Dismiss Message to cancel'),
        components=[
            ActionRow(
                components=[
                    button_delete_all_data
                ]
            )
        ]
    )


async def _import_confirm(
    interaction: Interaction,
    logs: list[str],
    key: str
) -> None:
    log = '\n'.join(logs)

    await _send_or_update(
        interaction,
        embed=Embed.warning('\n'.join([
            'Import attempt produced the following warnings:',
            '```',
            log if len(log) < 4040 else f'{log[:4037]}...',
            '```'])),
        components=[
            ActionRow(components=[
                button_import_anyway.with_overrides(
                    extra=[key]
                )
            ])
        ]
    )


async def _delete_group(
    interaction: Interaction,
    group: Group
) -> None:
    warning = dedent(
        f"""
        Are you sure you want to delete group `{group.name}`?

        This action is irreversible.
        """
    ).strip()

    if group.members:
        warning = dedent(
            f"""
            **WARNING: This group has {len(group.members)} members**.

            Deleting this group will delete all members alongside it.

            Please move members to another group before deleting if you wish to keep them.

            {warning}
            """
        ).strip()

    await _send_or_update(
        interaction,
        embed=(
            Embed(
                title='Delete Group',
                description=warning,
                color=0xff6969)
        ).set_footer(
            text='Click Dismiss Message to cancel'),
        components=[
            ActionRow(
                components=[
                    button_delete_group.with_overrides(
                        extra=[group]
                    )
                ]
            )
        ]
    )
