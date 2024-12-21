from src.discord import Interaction, InteractionContextType, ApplicationCommandOption, ApplicationCommandOptionType, Embed, ApplicationIntegrationType, Attachment, SlashCommandGroup, User, Channel
from src.db import ProxyMember, Group, GroupShare, ImageExtension
from src.errors import InteractionError
from asyncio import gather


group = SlashCommandGroup(
    name='group',
    description='manage your groups',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL()
)

group_set = group.create_subgroup(
    name='set',
    description='set group properties'
)

group_channels = group.create_subgroup(
    name='channels',
    description='manage a group\'s channels'
)


@group.command(
    name='new',
    description='create a new group',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='name of the group',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_new(
    interaction: Interaction,
    name: str
) -> None:
    if await Group.find_one({'accounts': interaction.author_id, 'name': name}):
        raise InteractionError(
            f'you already have a group with the name `{name}`')

    group = Group(
        name=name,
        accounts={interaction.author_id},
        avatar=None,
        tag=None,
    )

    await gather(
        group.save(),
        interaction.response.send_message(
            embeds=[Embed.success(f'created group `{name}`')]
        )
    )


@group.command(
    name='remove',
    description='remove a group',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to remove',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='from_account',
            description='only remove the group from this account; groups must always be attached to at least one account',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='with_members',
            description='delete all members in the group',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_remove(
    interaction: Interaction,
    group: Group,
    from_account: bool = False,
    with_members: bool = False
) -> None:
    if from_account:
        if len(group.accounts) == 1:
            raise InteractionError(
                'groups must always be attached to at least one account\nplease use `/group remove` without the `from_account` option to delete the group entirely')

        group.accounts.discard(interaction.author_id)

        await gather(
            group.save(),
            interaction.response.send_message(
                embeds=[Embed.success(
                    f'removed group `{group.name}` from your account')]
            )
        )
        return

    count = len(group.members)

    if group.members and not with_members:
        raise InteractionError(
            f'this group has {count} member{'s' if count-1 else ''}\nplease move them to other groups or use the `with_members` option to delete them')

    response = f'removed group `{group.name}`'

    tasks: list = [group.delete()]

    if with_members:
        response += (
            f' and all {count} of it\'s members'
            if count-1 else
            ' and it\'s only member'
        )

        tasks.extend([
            ProxyMember.find({'_id': {'$in': group.members}}).delete(),
        ])

    if group.avatar is not None:
        tasks.append(group.delete_avatar(interaction.author_id))

    await gather(
        *tasks,
        interaction.response.send_message(
            embeds=[Embed.success(response)]
        )
    )


@group.command(  # ! add pagination
    name='list',
    description='list your groups',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_list(
    interaction: Interaction
) -> None:
    groups = await Group.find({'accounts': interaction.author_id}).to_list()

    if not groups:
        raise InteractionError(
            'you don\'t have any groups, create one with `/group new`')

    await interaction.response.send_message(
        embeds=[Embed.success(
            '\n'.join(group.name for group in groups)
        )]
    )


@group.command(
    name='share',
    description='share a group with another account',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to share',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.USER,
            name='user',
            description='user to share with',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_share(
    interaction: Interaction,
    group: Group,
    user: User
) -> None:
    if user.id == interaction.author_id:
        raise InteractionError('you can\'t share a group with yourself')

    if user.id in group.accounts:
        raise InteractionError(
            f'the user {user.mention} already has access to this group')

    if await Group.find_one({'accounts': user.id, 'name': group.name}):
        raise InteractionError(
            f'the user {user.mention} already has a group with the name `{group.name}`')

    share = GroupShare(
        sharer=interaction.author_id,
        sharee=user.id,
        group=group.id
    )

    await gather(
        share.save(),
        interaction.response.send_message(
            embeds=[Embed.success('\n'.join([
                f'shared group `{group.name}` with {user.mention}',
                'they can accept by running `/group accept` in the next 24 hours'])
            )]
        )
    )


@group.command(
    name='accept',
    description='accept a group share',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.USER,
            name='user',
            description='user who shared the group',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_accept(
    interaction: Interaction,
    user: User
) -> None:
    share = await GroupShare.find_one({
        'sharee': interaction.author_id,
        'sharer': user.id
    })

    if share is None:
        raise InteractionError(
            f'you don\'t have any pending group shares from {user.username}')

    group = await Group.get(share.group)

    if group is None:
        raise InteractionError('the shared group no longer exists')

    group.accounts.add(interaction.author_id)

    await gather(
        group.save(),
        share.delete(),
        interaction.response.send_message(
            embeds=[Embed.success(f'accepted group `{group.name}`')]
        )
    )


@group_set.command(
    name='name',
    description='set a group\'s name',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to modify',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='new name',
            max_length=45,
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_set_name(
    interaction: Interaction,
    group: Group,
    name: str
) -> None:
    for account in group.accounts-{interaction.author_id}:
        for shared_group in await Group.find({'accounts;': account}).to_list():
            if shared_group.name == name:
                raise InteractionError(
                    f'the account <@{account}> already has a group with the name `{name}`\nplease remove the group from that account or choose a different name')

    old_name, group.name = group.name, name

    await gather(
        group.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'changed group name from `{old_name}` to `{name}`')]
        )
    )


@group_set.command(
    name='tag',
    description='set a group\'s tag',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to modify',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='tag',
            description='new tag (exclude to remove)',
            max_length=79,
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_set_tag(
    interaction: Interaction,
    group: Group,
    tag: str | None = None
) -> None:
    embeds = [
        Embed.success(f'set group `{group.name}` tag to `{tag}`')
    ]
    members = await group.get_members()

    if tag is not None:

        members_over_length = [
            member
            for member in members
            if len(f'{member.name} {tag}') > (
                32 if member.userproxy and member.userproxy.include_group_tag else 80
            )
        ]

        if members_over_length:
            members_str = 'the following members will have truncated tags when proxying messages:'

            for member in members_over_length:
                if len(f'{members_str}\n{member.name}') > 4096:
                    break
                members_str += f'\n{member.name}'

            embeds.append(Embed.warning(
                title=f'{len(members_over_length)
                         } members have names that are too long for this tag',
                message=members_str
            ))

    group.tag = tag

    await gather(
        group.save(),
        interaction.response.send_message(embeds=embeds)
    )

    sync_tasks = []
    failed = []

    for member in members:
        if not (member.userproxy and member.userproxy.include_group_tag):
            continue

        if tag and len(f'{member} {tag}') > 32:
            failed.append(member)
            continue

        from .member import _userproxy_sync
        from src.models import MemberUpdateType

        sync_tasks.append(_userproxy_sync(
            member, {MemberUpdateType.NAME}, interaction.author_name))

    if failed:
        await interaction.response.send_message(
            embeds=[Embed.warning(
                title='failed to update the following userproxies; their names with the group tag are too long',
                message='\n'.join(member.name for member in failed)
            )]
        )

    await gather(*sync_tasks)


@group_set.command(
    name='avatar',
    description='set a group\'s avatar',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to modify',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='new avatar (8MB max) (exclude to remove)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_group_set_avatar(
    interaction: Interaction,
    group: Group,
    avatar: Attachment | None = None
) -> None:
    if avatar is None:
        await gather(
            group.delete_avatar(interaction.author_id),
            interaction.response.send_message(
                embeds=[Embed.success(
                    f'removed group `{group.name}` avatar'
                )]
            )
        )
        return

    if avatar.size > 8_388_608:
        raise InteractionError('avatars must be less than 8MB')

    if (
        '.' in avatar.filename and
        avatar.filename.rsplit(
            '.', 1)[-1].lower() not in {'png', 'jpeg', 'jpg', 'gif', 'webp'}
    ):
        raise InteractionError('avatars must be a png, jpg, gif, or webp')

    await interaction.response.defer()

    await group.set_avatar(avatar.url, interaction.author_id)
    assert group.avatar is not None

    response = f'group `{group.name}` now has the avatar `{avatar.filename}`'

    if group.avatar.extension == ImageExtension.GIF:
        response += '\n\n**note:** gif avatars are not animated (unless in a userproxy)'

    await interaction.followup.send(
        embeds=[Embed.success(response)]
    )


@group_channels.command(
    name='add',
    description='restrict a group to a channel; useful for roleplay groups',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to modify',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.CHANNEL,
            name='channel',
            description='channel to restrict',
            required=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_group_channels_add(
    interaction: Interaction,
    group: Group,
    channel: Channel
) -> None:
    group.channels.add(channel.id)

    await gather(
        group.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'added channel {channel.mention} to group `{
                    group.name}` channel restrictions'
            )]
        )
    )


@group_channels.command(
    name='list',
    description='list the channels a group is restricted to',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to list',
            required=True,
            autocomplete=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_group_channels_list(
    interaction: Interaction,
    group: Group
) -> None:
    await interaction.response.send_message(
        embeds=[Embed.success(
            '\n'.join(
                f'<#{channel_id}>'
                for channel_id in group.channels
            )
        )]
    )


@group_channels.command(
    name='remove',
    description='remove a channel from a group',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to modify',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.CHANNEL,
            name='channel',
            description='channel to remove',
            required=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_group_channels_remove(
    interaction: Interaction,
    group: Group,
    channel: Channel
) -> None:
    group.channels.discard(channel.id)

    await gather(
        group.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'removed channel {channel.mention} from group `{group.name}` channel restrictions')]
        )
    )
