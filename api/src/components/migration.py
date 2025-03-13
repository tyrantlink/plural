from functools import partial
from asyncio import gather

from plural.db import Migration, Group, ProxyMember, Usergroup
from plural.errors import InteractionError, HTTPException
from plural.otel import span

from src.core.avatar import upload_avatar

from src.discord import (
    TextInputStyle,
    Application,
    ButtonStyle,
    Interaction,
    ActionRow,
    TextInput,
    button,
    Embed,
    modal,
    insert_cmd_ref
)

# ? yes this file is really bad and gross


PAGES = {
    'migrate': lambda interaction: _migrate(interaction)
}


@button(
    custom_id='migration_continue',
    label='Continue',
    style=ButtonStyle.SUCCESS)
async def migration_continue(
    interaction: Interaction
) -> None:
    await migration_loop(interaction)


@button(
    custom_id='migration_cancel',
    label='Cancel (all pending migrations will be deleted)',
    style=ButtonStyle.DANGER)
async def migration_cancel(
    interaction: Interaction
) -> None:
    match interaction.message.components[0].components[-1].label:
        case 'Cancel (all pending migrations will be deleted)':
            await interaction.response.update_message(
                components=[ActionRow(components=[
                    migration_continue,
                    migration_cancel.with_overrides(
                        label='Confirm Cancel')])])
        case 'Confirm Cancel':
            await Migration.find({
                'user': interaction.author_id
            }).delete()

            await interaction.response.send_message(embeds=[Embed.success(
                title='Migration Cancelled',
                message=(
                    'All pending migrations have been deleted\n\n'
                    'You can now use /plu/ral v3 from scratch'
                )
            )])
        case _:
            raise ValueError('Invalid button label')


@button(
    custom_id='migration_group_is_mine',
    label='Group is Mine',
    style=ButtonStyle.SUCCESS)
async def migration_group_is_mine(
    interaction: Interaction
) -> None:
    from src.core.http import GENERAL_SESSION

    migration = await Migration.find_one({
        'user': interaction.author_id,
        'phase': 0
    })

    if not migration:  # ? should never happen
        raise ValueError('Migration not found')

    group_data = migration.data[migration.index]

    group_data.pop('id')

    group_data['accounts'] = {
        (await Usergroup.get_by_user(
            interaction.author_id
        )).id
    }

    tasks = []

    avatar_url = group_data.pop('avatar', None)

    group = Group.model_validate(group_data)

    if avatar_url:
        tasks.append(upload_avatar(
            str(group.id),
            avatar_url,
            GENERAL_SESSION,
            True
        ))

    phase_1_migration = await Migration.find_one({
        'user': interaction.author_id,
        'phase': 1
    }) or Migration(
        user=interaction.author_id,
        phase=1,
        data=[],
        index=0
    )

    real_members = set()

    for member_id in group.members:
        member_data = migration.members[member_id]
        member_data.pop('id')
        avatar_url = member_data.pop('avatar', None)
        member = ProxyMember.model_validate(member_data)
        real_members.add(member.id)

        if avatar_url:
            tasks.append(upload_avatar(
                str(member.id),
                avatar_url,
                GENERAL_SESSION,
                True
            ))

        if member.userproxy and not member.userproxy.token:
            userproxy_data = member.userproxy.model_dump()
            userproxy_data['name'] = member.name
            userproxy_data['member_id'] = member.id
            member.userproxy = None
            phase_1_migration.data.append(userproxy_data)

        tasks.append(member.save())

    group.members = real_members

    tasks.append(group.save())

    if phase_1_migration.data:
        await phase_1_migration.save()

    embeds = interaction.message.embeds

    embeds[-1].set_footer(
        text='Importing... This may take a while'
    )

    await interaction.response.update_message(
        embeds=embeds,
        components=[ActionRow(
            components=[
                component.with_overrides(
                    disabled=True)
                for component in
                action_row.components])
            for action_row in
            interaction.message.components
        ]
    )

    await gather(*tasks)

    migration.index += 1
    await migration.save()

    await _handle_group_migration(interaction, migration)


@button(
    custom_id='migration_group_not_mine',
    label='Group is not Mine',
    style=ButtonStyle.DANGER)
async def migration_group_not_mine(
    interaction: Interaction
) -> None:
    migration = await Migration.find_one({
        'user': interaction.author_id,
        'phase': 0
    })

    if not migration:  # ? should never happen
        raise ValueError('Migration not found')

    migration.index += 1
    await migration.save()

    await _handle_group_migration(interaction, migration)


@modal(
    custom_id='modal_set_token',
    title='Set Token',
    text_inputs=[
        TextInput(
            custom_id='token',
            label='Token',
            placeholder='Token',
            style=TextInputStyle.SHORT)])
async def modal_set_token(
    interaction: Interaction,
    token: str
) -> None:
    from src.core.http import get_bot_id_from_token

    migration = await Migration.find_one({
        'user': interaction.author_id,
        'phase': 1
    })

    if not migration:  # ? should never happen
        raise ValueError('Migration not found')

    token = token.strip()

    token_bot_id = get_bot_id_from_token(token)

    userproxy_data = migration.data[migration.index]

    if token_bot_id != userproxy_data['bot_id']:
        raise InteractionError(
            'Token does not match userproxy bot id'
        )

    member = await ProxyMember.find_one({
        '_id': userproxy_data['member_id']
    })

    member.userproxy = ProxyMember.UserProxy.model_validate(
        userproxy_data | {'token': token}
    )

    try:
        await Application.fetch(token, False)
    except HTTPException as e:
        raise InteractionError(
            'Failed to fetch application. Token may be invalid'
        ) from e

    await member.save()

    migration.index += 1
    await migration.save()

    await _handle_userproxy_migration(interaction, migration)


@button(
    custom_id='migration_set_token',
    label='Set Token',
    style=ButtonStyle.SUCCESS)
async def migration_set_token(
    interaction: Interaction
) -> None:
    await interaction.response.send_modal(
        modal_set_token
    )


@button(
    custom_id='migration_skip',
    label='Skip (Userproxy will be deleted)',
    style=ButtonStyle.DANGER)
async def migration_skip(
    interaction: Interaction
) -> None:
    migration = await Migration.find_one({
        'user': interaction.author_id,
        'phase': 1
    })

    if not migration:  # ? should never happen
        raise ValueError('Migration not found')

    migration.index += 1
    await migration.save()

    await _handle_userproxy_migration(interaction, migration)


async def migration_loop(
    interaction: Interaction
) -> None:
    migrations = await Migration.find({
        'user': interaction.author_id
    }).to_list()

    if not migrations:
        await (
            partial(interaction.followup.edit_message, interaction.message.id)
            if interaction.response.responded else
            interaction.response.update_message
            if interaction.message else
            interaction.response.send_message
        )(
            embeds=[Embed.success(
                title='Migration Complete',
                message='You are now ready for /plu/ral v3')],
            components=[])

        from src.commands.userproxy import _userproxy_sync

        usergroup = await Usergroup.get_by_user(interaction.author_id)

        groups = await Group.find({
            'accounts': usergroup.id
        }).to_list()

        userproxies = {
            group: member
            for group in groups
            for member in await ProxyMember.find({
                '_id': {'$in': list(group.members)},
                'userproxy': {'$ne': None}
            }).to_list()
        }

        with span(f'bulk syncing {len(userproxies)} userproxies'):
            await gather(*(
                _userproxy_sync(
                    interaction,
                    userproxy,
                    {
                        'avatar',
                        'commands',
                        'event_webhooks_status',
                        'event_webhooks_types',
                        'event_webhooks_url',
                        'guilds'
                        'icon',
                        'install_params',
                        'integration_types_config',
                        'interactions_endpoint_url',
                        'username',
                    },
                    silent=True,
                    usergroup=usergroup,
                    group=group)
                for group, userproxy in userproxies.items()
            ))
        return

    migration = migrations[0]

    match migration.phase:
        case 0:
            await _handle_group_migration(interaction, migration)
        case 1:
            await _handle_userproxy_migration(interaction, migration)
        case _:
            raise ValueError('Invalid migration phase')


async def _handle_group_migration(
    interaction: Interaction,
    migration: Migration
) -> None:
    try:
        group = migration.data[migration.index]
    except IndexError:
        await Migration.delete(migration)
        await migration_loop(interaction)
        return

    await (
        partial(interaction.followup.edit_message, interaction.message.id)
        if interaction.response.responded else
        interaction.response.update_message
        if interaction.message else
        interaction.response.send_message
    )(
        embeds=[
            Embed.success(
                title='Group Migration',
                message=(
                    'You have groups that you have shared/have been shared with you\n\n'
                    '/plu/ral 3 has overhauled the group share system, '
                    'however due to the way the v2 system worked, the actual owner cannot be determined\n\n'
                    'Please go through every group and select the groups you own\n\n'
                    '(Copies are made with you as the owner)')),
            Embed(
                title=f'Group {migration.index+1}/{len(migration.data)}',
                color=0x69ff69
            ).add_field(
                name='Name',
                value=group['name'],
                inline=False
            ).add_field(
                name='Members',
                value='\n'.join([
                    migration.members.get(member_id)["name"]
                    for member_id in group['members'][:10]
                ]) + (
                    f'\n... and {len(group["members"])-10} more'
                    if len(group['members']) > 10 else ''))],
        components=[ActionRow(components=[
            migration_group_is_mine,
            migration_group_not_mine
        ])]
    )


async def _handle_userproxy_migration(
    interaction: Interaction,
    migration: Migration
) -> None:
    try:
        userproxy_data = migration.data[migration.index]
    except IndexError:
        await Migration.delete(migration)
        await migration_loop(interaction)
        return

    await (
        partial(interaction.followup.edit_message, interaction.message.id)
        if interaction.response.responded else
        interaction.response.update_message
        if interaction.message else
        interaction.response.send_message
    )(
        embeds=[
            Embed.success(
                title='Userproxy Migration',
                message=(
                    'In /plu/ral v3, userproxy tokens are required\n\n'
                    'Please go to [the developer portal](https://discord.com/developers/applications) and supply a token for each userproxy\n\n'
                    'see [the userproxy documentation](https://plural.gg/guide/userproxies#creating-a-userproxy) for more information')),
            Embed(
                title=f'Userproxy {migration.index+1}/{len(migration.data)}',
                color=0x69ff69
            ).add_field(
                name='Member Name',
                value=userproxy_data['name']
            ).add_field(
                name='Userproxy Bot',
                value=f'<@{userproxy_data['bot_id']}>')],
        components=[ActionRow(components=[
            migration_set_token,
            migration_skip
        ])]
    )


async def _migrate(
    interaction: Interaction
) -> bool:
    migrations = await Migration.find({
        'user': interaction.author_id
    }).to_list()

    if not migrations:
        return False

    with span('running migration'):
        await interaction.response.send_message(
            embeds=[Embed(
                title='Migration Required',
                color=0xff6969,
                description=insert_cmd_ref(
                    'You have data incompatible with /plu/ral v3\n\n'
                    'Please click continue below to migrate\n\n'
                    'NOTE: If you use multiple discord accounts and '
                    'this is **NOT** your main account, you should cancel this migration '
                    'and use your main account, then use {cmd_ref[account share]} '
                    'to synchronize your data across accounts\n\n'
                    'Data is duplicated for each account attached to a group, '
                    'so migration data will only be deleted for *this* account if you cancel'))],
            components=[ActionRow(components=[
                migration_continue,
                migration_cancel
            ])]
        )

    return True
