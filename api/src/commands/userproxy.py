from __future__ import annotations

from datetime import datetime, timedelta, UTC
from base64 import b64encode
from asyncio import gather
from regex import compile

from plural.db.enums import ReplyType, ReplyFormat
from plural.db import (
    Interaction as DBInteraction,
    Message as DBMessage,
    ProxyMember,
    Usergroup,
    Reply,
    Group
)
from plural.errors import (
    InteractionError,
    HTTPException,
    Unauthorized,
    Forbidden,
    NotFound
)

from src.core.models import (
    USERPROXY_FOOTER_LIMIT,
    USERPROXY_FOOTER,
    LEGACY_FOOTERS,
    env
)

from src.core.http import (
    get_bot_id_from_token,
    request,
    Route
)

from src.core.avatar import convert_for_userproxy

from src.discord.commands import sync_commands
from src.discord import (
    ApplicationCommandOptionType,
    ApplicationIntegrationType,
    ApplicationCommandScope,
    InteractionContextType,
    EventWebhooksStatus,
    ApplicationCommand,
    EventWebhooksType,
    SlashCommandGroup,
    AllowedMentions,
    message_command,
    slash_command,
    Attachment,
    Application,
    Permission,
    Interaction,
    MessageFlag,
    Message,
    Webhook,
    Embed
)

from src.components import PAGES

from .helpers import sed_edit, SED, format_reply
from .group import group_edit_check


COMMAND_NAME_REGEX = compile(
    r'^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$'
)

userproxy = SlashCommandGroup(
    name='userproxy',
    description='Manage your userproxies',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL()
)

userproxy_set = userproxy.create_subgroup(
    name='set',
    description='Set userproxy attributes'
)


async def sync_response(interaction: Interaction) -> None:
    await interaction.response.send_message(embeds=[Embed(
        title='Userproxy Sync in progress',
        description='This may take a few seconds',
        color=0x000000
    )])


async def _userproxy_sync(
    interaction: Interaction,
    member: ProxyMember,
    patch_filter: set,
    app: Application | None = None,
    include_attribution: bool = True,
    silent: bool = False,
    usergroup: Usergroup | None = None,
    group: Group | None = None,
) -> None:
    if member.userproxy is None:
        raise ValueError('Member has no userproxy')

    if not silent:
        await sync_response(interaction)

    try:
        app = app or await Application.fetch(
            member.userproxy.token,
            False)
    except HTTPException as e:
        raise InteractionError(
            'Invalid bot token\n\nPlease go to the '
            f'[discord developer portal](https://discord.com/developers/applications/{member.userproxy.bot_id}/bot) '
            'to reset the token'
        ) from e

    usergroup = (
        usergroup or
        await Usergroup.get_by_user(
            interaction.author_id,
            use_cache=False
        )
    )

    group = group or await member.get_group(False)

    base_app_patch: dict = {
        'interactions_endpoint_url': (
            f'https://{'testing' if env.dev else 'api'}.{env.domain}/interaction'
            if not usergroup.userproxy_config.self_hosted else
            None),
        'event_webhooks_url': f'https://{'testing' if env.dev else 'api'}.{env.domain}/event',
        'event_webhooks_types': [
            EventWebhooksType.APPLICATION_AUTHORIZED.value],
        'event_webhooks_status': EventWebhooksStatus.ENABLED.value
    }

    app_patch: dict = {
        'integration_types_config': {'0': {}, '1': {}},
        'install_params': None
    }

    bot_patch: dict = {}

    if not patch_filter or 'commands' in patch_filter:
        await sync_commands(
            member.userproxy.token,
            interaction.author_id
        )

    if not patch_filter or 'guilds' in patch_filter:
        member.userproxy.guilds = {
            int(guild.id)
            for guild in
            await app.bot.fetch_guilds(member.userproxy.token)
        }

    if not patch_filter or 'username' in patch_filter:
        bot_patch['username'] = (
            f'{member.name}' + (
                f' {group.tag}' if (
                    group.tag and
                    usergroup.userproxy_config.include_group_tag
                ) else ''
            )
        )

    if not patch_filter or 'avatar' in patch_filter:
        if member.avatar:
            mime, avatar = await convert_for_userproxy(member)
        elif group.avatar:
            mime, avatar = await convert_for_userproxy(group)
        else:
            mime, avatar = None, None

        avatar_data = (
            f'data:{mime};base64,{b64encode(avatar).decode('ascii')}'
            if avatar else
            None
        )

        bot_patch['avatar'] = avatar_data
        app_patch['icon'] = avatar_data

    if not patch_filter or 'description' in patch_filter:
        current = app.description
        for footer in {USERPROXY_FOOTER, *LEGACY_FOOTERS}:
            current = current.removesuffix(footer.format(
                username=interaction.author_name
            )).strip()

        app_patch['description'] = (
            f'{current}\n\n' + (USERPROXY_FOOTER.format(
                username=interaction.author_name
            ) if include_attribution else '')
        ).strip()[:400]

    base_app_patch = {
        k: v
        for k, v in base_app_patch.items()
        if not patch_filter or k in patch_filter
    }

    app_patch = {
        k: v
        for k, v in app_patch.items()
        if not patch_filter or k in patch_filter
    }

    bot_patch = {
        k: v
        for k, v in bot_patch.items()
        if not patch_filter or k in patch_filter
    }

    if base_app_patch:
        app = await app.patch(
            member.userproxy.token,
            base_app_patch
        )

    tasks = []

    if app_patch:
        tasks.append(app.patch(
            member.userproxy.token,
            app_patch
        ))

    if bot_patch:
        tasks.append(request(
            Route(
                'PATCH',
                '/users/@me',
                member.userproxy.token),
            json=bot_patch
        ))

    await gather(*tasks)


async def userproxy_sync(
    interaction: Interaction,
    member: ProxyMember,
    patch_filter: set,
    app: Application | None = None,
    include_attribution: bool = True,
    silent: bool = False
) -> None:
    try:
        await _userproxy_sync(
            interaction,
            member,
            patch_filter,
            app,
            include_attribution,
            silent)
    except BaseException:
        await interaction.followup.edit_message(
            '@original',
            embeds=[Embed.error(
                title='Error syncing userproxy',
                message='Details provided in followup'
            )])
        raise


async def _delete_userproxy(
    userproxy: ProxyMember
) -> None:
    responses = await gather(
        request(Route(
            'PUT',
            '/applications/{application_id}/commands',
            application_id=userproxy.userproxy.bot_id,
            token=userproxy.userproxy.token),
            json=[]),
        request(
            Route(
                'PATCH',
                '/applications/{application_id}',
                application_id=userproxy.userproxy.bot_id,
                token=userproxy.userproxy.token),
            json={
                'interactions_endpoint_url': None,
                'event_webhooks_url': None,
                'event_webhooks_types': [],
                'event_webhooks_status': EventWebhooksStatus.DISABLED.value}),
        return_exceptions=True
    )

    for response in responses:
        if isinstance(response, Exception):
            raise response

    userproxy.userproxy = None


async def _permission_check(
    interaction: Interaction
) -> bool:
    if not (interaction.member and interaction.member.permissions):
        return False

    error = ''

    if not interaction.member.permissions & Permission.SEND_MESSAGES:
        error = 'you do not have permission to send messages in this channel'

    if not interaction.member.permissions & Permission.USE_EXTERNAL_APPS:
        error = 'you do not have permission to use external apps in this server'

    if not error:
        return False

    await interaction.response.send_message(
        embeds=[Embed.error(error)]
    )

    return True


@userproxy.command(
    name='edit',
    description='Edit a userproxy',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='Userproxy to edit',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='command',
            description='Update /proxy command name',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='token',
            description='Update bot token',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_userproxy_edit(
    interaction: Interaction,
    userproxy: ProxyMember,
    command: str | None = None,
    token: str | None = None
) -> None:
    assert isinstance(userproxy.userproxy, ProxyMember.UserProxy)
    sync_filter: set[str] = set()
    warning = ''

    if token is not None:
        bot_id = get_bot_id_from_token(token)

        app = await Application.fetch(token, False)

        if userproxy.userproxy.bot_id != bot_id:
            warning = (
                'Warning: Changing to a new bot will cause '
                'the old bot to lose its userproxy commands'
            )

            new_userproxy = ProxyMember.UserProxy(
                bot_id=bot_id,
                public_key=app.verify_key,
                token=token,
                command=userproxy.userproxy.command,
                guilds=set()
            )

            sync_filter.update(
                'avatar',
                'commands',
                'description',
                'event_webhooks_status',
                'event_webhooks_types',
                'event_webhooks_url',
                'guilds',
                'icon',
                'install_params',
                'integration_types_config',
                'interactions_endpoint_url',
                'username'
            )

            await _delete_userproxy(userproxy)

            userproxy.userproxy = new_userproxy

        userproxy.userproxy.token = token

    if command is not None:
        proxy_command = command.lstrip('/').lower()

        if not COMMAND_NAME_REGEX.match(proxy_command):
            raise InteractionError(
                'Invalid proxy command\n\n'
                'Commands must be 1-32 characters and only contain '
                'letters, numbers, hyphens, and underscores'
            )

        sync_filter.add('commands')

        userproxy.userproxy.command = proxy_command

    await userproxy.save()  # type: ignore[call-arg]

    await userproxy_sync(
        interaction,
        userproxy,
        sync_filter,
        locals().get('app'),
        False
    )

    embed = Embed.success(
        title='Userproxy Edited',
        message=(
            'Userproxy edited successfully' +
            f'\n\n{warning}' if warning else ''
        )
    ).set_footer(
        'You may need to refresh Discord to see the changes'
    )

    await interaction.followup.edit_message(
        '@original',
        embeds=[embed]
    )


@userproxy.command(
    name='invite',
    description='Get a userproxy invite link',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='Userproxy to invite',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_userproxy_invite(
    interaction: Interaction,
    userproxy: ProxyMember
) -> None:
    await interaction.response.send_message(
        embeds=[Embed.success(
            title='Invite Userproxy',
            message=(
                '[Add the bot to your account]'
                '(https://discord.com/oauth2/authorize?client_id='
                f'{userproxy.userproxy.bot_id}&integration_type=1'
                '&scope=applications.commands)\n\n'
                '[Invite the bot to a server]'
                '(https://discord.com/oauth2/authorize?client_id='
                f'{userproxy.userproxy.bot_id}&permissions=0'
                '&integration_type=0&scope=bot)'
            )
        )]
    )


@userproxy.command(
    name='new',
    description='Create a new userproxy (see /help)',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to give userproxy',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='bot_token',
            description='Bot token to use for userproxy',
            required=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_command',
            description='Command to use when proxying (Default: /proxy)',
            min_length=1,
            max_length=32,
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='keep_avatar',
            description='Keep the bot\'s current avatar (Default: False)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_userproxy_new(
    interaction: Interaction,
    member: ProxyMember,
    bot_token: str,
    proxy_command: str = 'proxy',
    keep_avatar: bool = False
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    if member.userproxy:
        raise InteractionError(
            f'Member `{member.name}` already has a userproxy\n\n'
            'Use {cmd_ref[userproxy remove]} to remove it'
        )

    if not (2 <= len(member.name) <= 32):
        raise InteractionError(
            'Member name must be 2-32 characters long to create a userproxy'
        )

    bot_token = bot_token.strip()  # ? discord does this, but just in case
    bot_id = get_bot_id_from_token(bot_token)
    proxy_command = proxy_command.lstrip('/').lower()

    if not COMMAND_NAME_REGEX.match(proxy_command):
        raise InteractionError(
            'Invalid proxy command\n\n'
            'Commands must be 1-32 characters and only contain letters, numbers, hyphens, and underscores'
        )

    potential_userproxy = await ProxyMember.find_one({
        'userproxy.bot_id': bot_id
    })

    if potential_userproxy is not None:
        raise InteractionError(
            f'Userproxy with bot <@{bot_id}> already exists\n\n'
            'Please use a new bot token'
        )

    try:
        app = await Application.fetch(bot_token, False)
    except HTTPException as e:
        raise InteractionError(
            'Invalid bot token\n\nPlease go to the '
            f'[discord developer portal](https://discord.com/developers/applications/{bot_id}/bot) '
            'to reset the token'
        ) from e

    member.userproxy = ProxyMember.UserProxy(
        bot_id=bot_id,
        public_key=app.verify_key,
        token=bot_token,
        command=proxy_command
    )

    await member.save()

    await userproxy_sync(
        interaction,
        member,
        {
            'interactions_endpoint_url',
            'event_webhooks_url',
            'event_webhooks_types',
            'event_webhooks_status',
            'integration_types_config',
            'install_params',
            'commands',
            'guilds',
            'username',
            'description',
        } if keep_avatar else set(),
        app
    )

    await interaction.followup.edit_message(
        '@original',
        embeds=[Embed.success(
            title='Userproxy Created',
            message=(
                f'Userproxy for {member.name} created successfully\n\n'
                '[Add the bot to your account]'
                '(https://discord.com/oauth2/authorize?client_id='
                f'{member.userproxy.bot_id}&integration_type=1'
                '&scope=applications.commands)'
            )
        )]
    )


@userproxy.command(
    name='remove',
    description='Remove a userproxy (DOES NOT DELETE THE MEMBER OR BOT)',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='Member to remove userproxy from',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_userproxy_remove(
    interaction: Interaction,
    userproxy: ProxyMember
) -> None:
    await sync_response(interaction)

    try:
        await _delete_userproxy(userproxy)

        await gather(
            userproxy.save(),
            interaction.followup.edit_message(
                '@original',
                embeds=[Embed.success(
                    title='Userproxy Removed',
                    message=f'Userproxy for `{userproxy.name}` removed successfully')]))
    except Unauthorized:
        userproxy.userproxy = None

        await gather(
            userproxy.save(),
            await interaction.send(
                embeds=[Embed.success(
                    title='Userproxy Removed',
                    message=(
                        'Userproxy removed, but the token was invalid.\n\n'
                        '/plu/ral was not able to remove the commands.'
                    )
                )]
            )
        )


@userproxy.command(
    name='sync',
    description='Sync member with userproxy, generally not required unless something is broken',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='Member to sync',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='sync_avatar',
            description='Sync avatar (default: False)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_userproxy_sync(
    interaction: Interaction,
    userproxy: ProxyMember,
    sync_avatar: bool = False
) -> None:
    await userproxy_sync(
        interaction,
        userproxy, {
            'commands',
            'event_webhooks_status',
            'event_webhooks_types',
            'event_webhooks_url',
            'guilds',
            'install_params',
            'integration_types_config',
            'interactions_endpoint_url',
            'username',
        } | ({'avatar', 'icon'} if sync_avatar else set()),
        None,
        False
    )

    await interaction.followup.edit_message(
        '@original',
        embeds=[Embed.success(
            title='Userproxy Synced',
            message=f'Userproxy for {userproxy.name} synced successfully'
        )]
    )


@userproxy_set.command(
    name='banner',
    description='Set a userproxy\'s banner',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='Userproxy to give new banner',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='banner',
            description='New userproxy banner (max 15MB) (leave blank to remove)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_userproxy_set_banner(
    interaction: Interaction,
    userproxy: ProxyMember,
    banner: Attachment | None = None
) -> None:
    await sync_response(interaction)

    if banner:
        banner = await banner.to_image_data(15_728_640)

    await request(Route(
        'PATCH',
        '/users/@me',
        userproxy.userproxy.token),
        json={'banner': banner}
    )

    await interaction.followup.edit_message(
        '@original',
        embeds=[Embed.success(
            title='Userproxy Banner Set',
            message='Userproxy banner set successfully'
        ).set_footer(
            'You may need to refresh Discord to see the changes'
        )]
    )


@userproxy_set.command(
    name='bio',
    description='Set a userproxy\'s bio',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            max_length=USERPROXY_FOOTER_LIMIT,
            description='Userproxy to give new bio (you\'ll type the bio in a prompt)',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='include_attribution',
            description='Whether to add /plu/ral attribution to the end of the bio (default: True)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_bio(
    interaction: Interaction,
    userproxy: ProxyMember,
    include_attribution: bool = True
) -> None:
    await PAGES['bio'](
        interaction,
        userproxy,
        include_attribution
    )


@userproxy_set.command(
    name='nickname',
    description='Set a userproxy\'s nickname in this server (bot must be added to the server)',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='Userproxy to nickname',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='nickname',
            description='New nickname (leave blank to remove)',
            max_length=32,
            required=False)],
    contexts=[InteractionContextType.GUILD],
    integration_types=ApplicationIntegrationType.ALL())
async def slash_userproxy_set_nickname(
    interaction: Interaction,
    userproxy: ProxyMember,
    nickname: str | None = None
) -> None:
    if interaction.guild_id not in userproxy.userproxy.guilds:
        raise InteractionError(
            'Userproxy bot is not in this server.\n\n'
            'Use {cmd_ref[userproxy invite]} to get an invite link'
        )

    try:
        await interaction.guild.modify_current_member(
            userproxy.userproxy.token,
            nick=nickname)
    except NotFound as e:
        raise InteractionError(
            'Userproxy bot is not in this server.\n\n'
            'Use {cmd_ref[userproxy invite]} to get an invite link'
        ) from e
    except Forbidden as e:
        raise InteractionError(
            'Userproxy bot does not have the change '
            'nickname permission in this server'
        ) from e

    await interaction.response.send_message(
        embeds=[Embed.success(
            f'Userproxy <@{userproxy.userproxy.bot_id}> '
            f'nickname set to `{nickname}`'
        )]
    )


@message_command(
    name='Reply',
    scope=ApplicationCommandScope.USERPROXY,
    contexts=InteractionContextType.ALL(),
    integration_types=[ApplicationIntegrationType.USER_INSTALL])
async def umessage_reply(
    interaction: Interaction,
    message: Message
) -> None:
    if await _permission_check(interaction):
        return

    reply = await Reply.find_one({
        'bot_id': interaction.application_id,
        'channel': interaction.channel_id or 0,
        'type': ReplyType.QUEUE
    })

    if reply is None:
        await gather(
            PAGES['proxy'](
                interaction,
                False,
                message),
            Reply(
                type=ReplyType.REPLY,
                bot_id=interaction.application_id,
                channel=interaction.channel_id or 0,
                content=message.content,
                attachments=[
                    Reply.Attachment(
                        url=attachment.url,
                        filename=attachment.filename,
                        description=attachment.description or None)
                    for attachment in message.attachments],
                message_id=message.id,
                author=Reply.Author(
                    id=message.author.id,
                    global_name=message.author.global_name,
                    username=message.author.username,
                    avatar=message.author.avatar),
                webhook_id=message.webhook_id or None,
                ts=datetime.now(UTC) + timedelta(minutes=15)
            ).save())
        return

    if reply.attachments:
        await interaction.response.defer(MessageFlag.NONE)

    attachments = [
        await Attachment.from_reply_attachment(
            attachment).to_file()
        for attachment in reply.attachments
    ]

    usergroup = await Usergroup.get_by_user(interaction.author_id)

    reply_format = (
        usergroup.userproxy_config.reply_format
        if interaction.context == InteractionContextType.GUILD else
        usergroup.userproxy_config.dm_reply_format
    )

    reply_insert, mention_ignore = format_reply(
        reply.content or '',
        message,
        reply_format,
        interaction.guild_id or None
    )

    embeds = []

    match reply_insert:
        case str():
            reply.content = reply_insert
        case Embed():
            embeds.append(reply_insert)

    mentions = AllowedMentions.parse_content(
        reply.content,
        False,
        mention_ignore
    )

    if not (
        reply_format == ReplyFormat.INLINE and
        usergroup.userproxy_config.ping_replies
    ):  # ? mentions.users will never be None as we just created it
        mentions.users.discard(message.author.id)

    sent_message = await interaction.send(
        reply.content,
        embeds=embeds,
        allowed_mentions=mentions,
        attachments=attachments,
        with_response=True,
        flags=MessageFlag.NONE
    )

    await gather(
        reply.delete(),
        DBInteraction(
            author_id=interaction.author_id,
            bot_id=interaction.application_id,
            message_id=sent_message.id,
            channel_id=sent_message.channel_id,
            token=interaction.token,
        ).save()
    )


@slash_command(
    name='proxy',
    description='Send a message',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='message',
            min_length=0,
            max_length=2000,
            description='Message to send',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='queue_for_reply',
            description='Queue for reply',
            required=False
        )]+[ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name=f'attachment{i}' if i else 'attachment',
            description='Send an attachment',
            required=False
        ) for i in range(10)],
    scope=ApplicationCommandScope.USERPROXY,
    contexts=InteractionContextType.ALL(),
    integration_types=[ApplicationIntegrationType.USER_INSTALL])
async def uslash_proxy(
    interaction: Interaction,
    message: str | None = None,
    queue_for_reply: bool = False,
    **_attachments: Attachment,
) -> None:
    if await _permission_check(interaction):
        return

    attachments = list(_attachments.values())

    if not message and not attachments:
        await PAGES['proxy'](
            interaction,
            queue_for_reply,
            None)
        return

    if message and SED.match(message):
        old_interaction = await DBInteraction.find_one({
            'author_id': interaction.author_id,
            'bot_id': interaction.application_id,
            'channel_id': interaction.channel_id},
            sort=[('ts', -1)]
        )

        if old_interaction is None:
            raise InteractionError(
                'No message found\n\n'
                'Messages older than 15 minutes cannot be edited'
            )

        webhook = Webhook.from_proxy_interaction(old_interaction)
        og_message = await webhook.fetch_message(
            old_interaction.message_id
        )

        await sed_edit(
            interaction,
            og_message,
            message,
            webhook
        )

        return

    if attachments:
        if not interaction.app_permissions & Permission.ATTACH_FILES:
            raise InteractionError(
                'Userproxy bot does not have permission to attach files in this channel'
            )

        limit = (
            interaction.guild.filesize_limit
            if interaction.guild else
            10_485_760
        )

        if sum(
            attachment.size
            for attachment in
            attachments
        ) > limit:
            raise InteractionError(
                f'Attachments exceed the {limit / 1_048_576}MB limit'
                ' for this channel'
            )

        if not queue_for_reply:
            await interaction.response.defer(MessageFlag.NONE)

    if not queue_for_reply:
        sent_message = await interaction.send(
            message,
            attachments=[
                await attachment.to_file()
                for attachment in
                attachments],
            with_response=True,
            flags=MessageFlag.NONE
        )

        await gather(
            DBInteraction(
                author_id=interaction.author_id,
                bot_id=interaction.application_id,
                message_id=sent_message.id,
                channel_id=interaction.channel_id,
                token=interaction.token
            ).save(),
            DBMessage(
                original_id=None,
                proxy_id=sent_message.id,
                author_id=interaction.author_id,
                channel_id=interaction.channel_id,
                member_id=(await ProxyMember.find_one({
                    'userproxy.bot_id': interaction.application_id
                })).id,
                reason='Userproxy /proxy command'
            ).save())
        return

    await gather(
        Reply(
            type=ReplyType.QUEUE,
            bot_id=interaction.application_id,
            channel=interaction.channel_id or 0,
            content=message,
            attachments=[
                Reply.Attachment(
                    url=attachment.url,
                    filename=attachment.filename,
                    description=attachment.description or None)
                for attachment in attachments],
            message_id=None,
            author=None,
            webhook_id=None,
            ts=datetime.now(UTC) + timedelta(minutes=5)
        ).save(),
        interaction.send(embeds=[Embed.success(
            title='Message Queued for Reply',
            message='Use the Reply message command within the next 5 minutes to send the message'
        )])
    )
