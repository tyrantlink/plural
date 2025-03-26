from __future__ import annotations

from asyncio import gather

from plural.db.enums import GroupSharePermissionLevel, ShareType
from plural.db import Group, Usergroup, Share
from plural.errors import InteractionError

from src.discord import (
    ApplicationCommandOptionType,
    ApplicationIntegrationType,
    InteractionContextType,
    ApplicationCommand,
    SlashCommandGroup,
    Interaction,
    Attachment,
    Channel,
    Embed,
    User
)

from src.components import PAGES

from .helpers import set_avatar, delete_avatar, group_edit_check


async def _set_tag(
    interaction: Interaction,
    group: Group,
    tag: str | None
) -> list[Embed]:
    from .userproxy import _userproxy_sync

    usergroup = await Usergroup.get_by_user(interaction.author_id)

    embeds = [Embed.success(
        f'Set group `{group.name}` tag to `{tag}`'
        if tag else
        f'Removed group `{group.name}` tag'
    )]

    members = await group.get_members()

    members_over_length = [
        member for member in members
        if len(f'{member.name} {tag}') > (
            32
            if usergroup.userproxy_config.include_group_tag else
            80
        )
    ] if tag else []

    if members_over_length:
        warning_message = 'The following members will have their names truncated:\n'

        for member in members_over_length:
            if len(f'{warning_message}\n{member.name}') > 4096:
                warning_message = warning_message[:4093] + '...'
                break

            warning_message += f'\n{member.name}'

        embeds.append(Embed.warning(
            title=f'{len(members_over_length)} have names that are too long for this tag',
            message=warning_message
        ).set_footer(
            text='Your group tag was still set.'
        ))

    group.tag = tag

    userproxy_members = [
        member
        for member in
        members
        if member.userproxy
    ]

    if userproxy_members:
        embeds[0].set_footer(
            'Note: you may need to refresh your Discord client '
            'to see changes to userproxy bots'
        )

        await gather(*[
            _userproxy_sync(
                interaction,
                userproxy,
                {'username'},
                silent=True,
                group=group)
            for userproxy in userproxy_members
        ])

    return embeds


group = SlashCommandGroup(
    name='group',
    description='Manage your groups',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL()
)

group_set = group.create_subgroup(
    name='set',
    description='Set group attributes'
)

group_channels = group.create_subgroup(
    name='channels',
    description='Restrict group to specific channels'
)


@group.command(
    name='accept',
    description='Accept a group shared to you',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.USER,
            name='user',
            description='User who shared the group',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_accept(
    interaction: Interaction,
    user: User
) -> None:
    share = await Share.find_one({
        'type': ShareType.GROUP,
        'sharer': user.id,
        'sharee': interaction.author_id
    })

    if share is None:
        raise InteractionError(
            f'<@{user.id}> did not share a group with you.'
        )

    group = await Group.get(share.group)

    if group is None:
        await share.delete()
        raise InteractionError(
            f'The group shared by <@{user.id}> no longer exists.'
        )

    sharer = await Usergroup.get_by_user(user.id)
    sharee = await Usergroup.get_by_user(interaction.author_id)

    if (
        group.account in {sharer.id, sharee.id} or
        share.permission_level is None
    ):
        await share.delete()
        raise InteractionError(
            'Invalid group share.'
        )

    existing_group = await Group.find_one({
        '$or': [
            {'account': sharee.id},
            {f'users.{interaction.author_id}': {'$exists': True}}],
        'name': group.name
    })

    if existing_group is not None:
        await share.delete()
        raise InteractionError(
            f'You already have a group named `{group.name}`.'
        )

    group.users[interaction.author_id] = share.permission_level

    await gather(
        group.save(),
        share.delete(),
        interaction.send(embeds=[Embed.success(
            f'Accepted group `{group.name}`'
        )])
    )


@group.command(
    name='info',
    description='Get information about a group',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to get information about',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_info(
    interaction: Interaction,
    group: Group
) -> None:

    embed = Embed(
        title=group.name,
        color=0x69ff69
    ).add_field(
        name='Tag',
        value=group.tag or 'None',
        inline=False
    ).add_field(
        name='Members',
        value=str(len(group.members)),
        inline=False
    )

    if group.avatar_url:
        embed.set_thumbnail(
            url=group.avatar_url
        )

    await interaction.response.send_message(embeds=[
        embed
    ])


@group.command(
    name='kick',
    description='Kick a user from a group share',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to kick from',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.USER,
            name='user',
            description='User to kick',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_kick(
    interaction: Interaction,
    group: Group,
    user: User
) -> None:
    usergroup = await Usergroup.get_by_user(interaction.author_id)

    if usergroup.id != group.account:
        raise InteractionError(
            'You must be an owner of this group to kick users.'
        )

    if user.id not in group.users:
        raise InteractionError(
            f'<@{user.id}> is not a member of this group.'
        )

    group.users.pop(user.id)

    await gather(
        group.save(),
        interaction.send(embeds=[Embed.success(
            f'Kicked <@{user.id}> from group `{group.name}`'
        )])
    )


@group.command(
    name='list',
    description='List your groups',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_list(
    interaction: Interaction
) -> None:
    await PAGES['pagination'](interaction, 'group', None)


@group.command(
    name='new',
    description='Create a new group',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='Name of the group',
            max_length=45,
            required=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='Avatar for the group (4MB max)',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='tag',
            description='Tag of the group, used in member names',
            max_length=79,
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_new(
    interaction: Interaction,
    name: str,
    avatar: Attachment | None = None,
    tag: str | None = None
) -> None:
    usergroup = await Usergroup.get_by_user(interaction.author_id)

    if await Group.find_one({
        '$or': [
            {'account': usergroup.id},
            {f'users.{interaction.author_id}': {'$exists': True}}],
        'name': name
    }):
        raise InteractionError(
            f'You already have a group named `{name}`.',)

    group = Group(
        name=name,
        account=usergroup.id
    )

    if avatar:
        await interaction.response.defer()
        await set_avatar(group, avatar.url, interaction.author_id)

    if tag:
        await _set_tag(interaction, group, tag)

    await gather(
        group.save(),
        interaction.send(embeds=[Embed.success(
            f'Created group `{name}`'
        )])
    )


@group.command(
    name='remove',
    description='Remove a group / leave a group (if shared)',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to remove',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_remove(
    interaction: Interaction,
    group: Group
) -> None:
    if interaction.author_id in group.users:
        group.users.pop(interaction.author_id)

        await gather(
            group.save(),
            interaction.send(embeds=[Embed.success(
                f'Removed group `{group.name}`'
            )])
        )

        return

    group_edit_check(group, interaction.author_id, True)

    await PAGES['delete_group'](interaction, group)


@group.command(
    name='share',
    description='Share a group with another user',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to share',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.USER,
            name='user',
            description='User to share with',
            required=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='permission_level',
            description='Permission level for the user',
            choices=[
                ApplicationCommand.Option.Choice(
                    name='Proxy Only',
                    value=str(GroupSharePermissionLevel.PROXY_ONLY.value)),
                ApplicationCommand.Option.Choice(
                    name='Full Access',
                    value=str(GroupSharePermissionLevel.FULL_ACCESS.value))],
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_share(
    interaction: Interaction,
    group: Group,
    user: User,
    permission_level: str
) -> None:
    group_edit_check(group, interaction.author_id, True)

    if user.id == interaction.author_id:
        raise InteractionError('You cannot share a group with yourself.')

    if user.id in group.users:
        raise InteractionError(
            f'<@{user.id}> is already a group member.'
        )

    share = await Share.find_one({
        'type': ShareType.GROUP,
        'sharer': interaction.author_id,
        'sharee': user.id
    })

    if share is not None:
        raise InteractionError(
            'You can only have one pending group share per user.'
        )

    sharer = await Usergroup.get_by_user(interaction.author_id)
    sharee = await Usergroup.get_by_user(user.id)

    if sharer.id == sharee.id:
        raise InteractionError(
            f'You and <@{user.id}> are in the same usergroup.\n\n'
            'Your groups are inherently shared.'
        )

    if sharer.id != group.account:
        raise InteractionError(
            'You cannot share a group that has been shared with you.\n\n'
            'Ask a group owner to share the group.'
        )

    if sharee.id == group.account:
        raise InteractionError(
            f'<@{user.id}> is already a group owner.'
        )

    await gather(
        Share(
            type=ShareType.GROUP,
            sharer=interaction.author_id,
            sharee=user.id,
            group=group.id,
            permission_level=GroupSharePermissionLevel(int(permission_level))
        ).save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'Shared group `{group.name}` with <@{user.id}>\n\n'
                'They can accept by running {cmd_ref[group accept]} '
                'within the next 6 hours',
                insert_command_ref=True
            )]
        )
    )


@group_channels.command(
    name='add',
    description='Restrict a group to a channel',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to restrict',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.CHANNEL,
            name='channel',
            description='Channel to restrict group to',
            required=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_group_channels_add(
    interaction: Interaction,
    group: Group,
    channel: Channel
) -> None:
    group_edit_check(group, interaction.author_id, True)

    group.channels.add(channel.id)

    await gather(
        group.save(),
        interaction.send(embeds=[Embed.success(
            f'Restricted group `{group.name}` to {channel.mention}'
        )])
    )


@group_channels.command(
    name='clear',
    description='Remove all channel restrictions from a group',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to unrestrict',
            required=True,
            autocomplete=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_group_channels_clear(
    interaction: Interaction,
    group: Group
) -> None:
    group_edit_check(group, interaction.author_id, True)

    group.channels.clear()

    await gather(
        group.save(),
        interaction.send(embeds=[Embed.success(
            f'Cleared channel restrictions for group `{group.name}`'
        )])
    )


@group_channels.command(
    name='list',
    description='List the channels a group is restricted to',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to list',
            required=True,
            autocomplete=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_group_channels_list(
    interaction: Interaction,
    group: Group
) -> None:
    channels = '\n'.join(
        f'<#{channel_id}>'
        for channel_id in group.channels
    )

    if len(channels) > 4093:
        newline = channels[:4093].rfind('\n')

        channels = f'{channels[:newline]}\n...'

    await interaction.send(embeds=[Embed.success(
        title=f'Channel restrictions for group `{group.name}`',
        message=channels or 'No restrictions'
    )])


@group_channels.command(
    name='remove',
    description='Remove a channel from a group',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to unrestrict',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.CHANNEL,
            name='channel',
            description='Channel to remove',
            required=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_group_channels_remove(
    interaction: Interaction,
    group: Group,
    channel: Channel
) -> None:
    group_edit_check(group, interaction.author_id, True)

    group.channels.discard(channel.id)

    await gather(
        group.save(),
        interaction.send(embeds=[Embed.success(
            f'Removed {channel.mention} from group `{group.name}` restrictions'
        )])
    )


@group_set.command(
    name='avatar',
    description='Set a group\'s avatar',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to modify',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='New avatar (4MB max) (exclude to remove)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_set_avatar(
    interaction: Interaction,
    group: Group,
    avatar: Attachment | None = None
) -> None:
    group_edit_check(group, interaction.author_id, True)

    await interaction.response.defer()

    if avatar:
        await set_avatar(group, avatar.url, interaction.author_id)
        message = f'Set group `{group.name}` avatar'
    else:
        await delete_avatar(group)
        message = f'Removed group `{group.name}` avatar'

    embed = Embed.success(message)

    userproxy_members = [
        member
        for member in
        await group.get_members()
        if (
            member.userproxy and
            member.avatar is None
        )
    ]

    if userproxy_members:
        from .userproxy import _userproxy_sync

        embed.set_footer(
            'Note: you may need to refresh your Discord client '
            'to see changes to userproxy bots'
        )

        await gather(*[
            _userproxy_sync(
                interaction,
                userproxy,
                {'avatar', 'icon'},
                silent=True,
                group=group)
            for userproxy in userproxy_members
        ])

    await interaction.send(embeds=[embed])


@group_set.command(
    name='name',
    description='Set a group\'s name',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to modify',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='New name',
            max_length=45,
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_set_name(
    interaction: Interaction,
    group: Group,
    name: str
) -> None:
    group_edit_check(group, interaction.author_id, True)

    if await Group.find_one({
        '$or': [
            {'account': group.account},
            {f'users.{interaction.author_id}': {'$exists': True}}],
        'name': name
    }):
        raise InteractionError(
            f'You already have a group named `{name}`.',)

    group.name = name

    await gather(
        group.save(),
        interaction.send(embeds=[Embed.success(
            f'Set group name to `{name}`'
        )])
    )


@group_set.command(
    name='tag',
    description='Set a group\'s tag',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to modify',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='tag',
            description='New tag (exclude to remove)',
            max_length=79,
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_set_tag(
    interaction: Interaction,
    group: Group,
    tag: str | None = None
) -> None:
    group_edit_check(group, interaction.author_id, True)

    embeds = await _set_tag(interaction, group, tag)

    await gather(
        group.save(),
        interaction.response.send_message(embeds=embeds)
    )
