from src.discord import slash_command, Interaction, message_command, InteractionContextType, Message, ApplicationCommandOption, ApplicationCommandOptionType, Embed, EmbedField, Permission, ApplicationIntegrationType, ApplicationCommandOptionChoice, Attachment, File, ActionRow, Webhook
from src.db import Message as DBMessage, ProxyMember, Latch, UserProxyInteraction, GuildConfig, UserConfig, ReplyFormat
from src.components import modal_plural_edit, umodal_edit, button_api_key, help_components, button_delete_all_data
from src.porting import StandardExport, PluralExport, PluralKitExport, TupperboxExport, LogMessage
from regex import match as regex_match, sub, error as RegexError, IGNORECASE, escape
from src.errors import InteractionError, Forbidden, PluralException
from src.logic.proxy import get_proxy_webhook, process_proxy
from src.version import VERSION, LAST_TEN_COMMITS
from src.models import DebugMessage, project
from src.discord.http import get_from_cdn
from pydantic_core import ValidationError
from asyncio import gather
from orjson import loads
from io import BytesIO
from time import time


SED_PATTERN = r'^s/(.*?)/(.*?)/?([gi]*)$'


async def _sed_edit(
    message: Message,
    sed: str
) -> tuple[str, Embed]:
    match = regex_match(SED_PATTERN, sed)

    if not match:
        raise InteractionError('invalid sed expression')

    expression, replacement, _raw_flags = match.groups()

    flags = 0
    count = 1

    for flag in _raw_flags:
        match flag:
            case 'g':
                count = 0
            case 'i':
                flags |= IGNORECASE
            case _:  # ? should never happen as it doesn't match the pattern
                raise InteractionError(f'invalid flag: {flag}')

    try:
        edited_content = sub(
            escape(expression), replacement, message.content, count=count, flags=flags)
    except RegexError:
        raise InteractionError('invalid regular expression')

    embed = (
        Embed.success('message edited')
        if edited_content != message.content else
        Embed.warning('no changes were made')
    )

    embed.set_footer(text=f'message id: {message.id}')

    return edited_content, embed


async def _userproxy_edit(interaction: Interaction, message: Message) -> bool:
    assert message.author is not None

    if not message.author.bot:
        return False

    member = await ProxyMember.find_one({'userproxy.bot_id': message.author.id})

    if member is None or member.userproxy is None:
        return False

    if interaction.author_id not in (await member.get_group()).accounts:
        raise InteractionError('you can only edit your own messages!')

    if member.userproxy.token is None:
        raise InteractionError(
            'you must have the bot token stored to edit messages')

    if (
        message.interaction_metadata is not None and
        await UserProxyInteraction.find_one({'message_id': message.id}) is None
    ):
        raise InteractionError(
            'due to discord limitations, you can\'t edit userproxy messages older than 15 minutes')

    await interaction.response.send_modal(
        modal=umodal_edit.with_title(
            'edit message'
        ).with_text_kwargs(
            0, value=message.content
        ).with_extra(
            message.id,
            message.author.id
        ))
    return True


@slash_command(
    name='ping', description='check the bot\'s latency',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_ping(interaction: Interaction) -> None:
    timestamp = (interaction.id >> 22) + 1420070400000

    await interaction.response.send_message(
        f'pong! ({round((time()*1000-timestamp))}ms)'
    )


@message_command(
    name='/plu/ral edit',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def message_plural_edit(interaction: Interaction, message: Message) -> None:
    if await _userproxy_edit(interaction, message):
        return

    if message.webhook_id is None:
        raise InteractionError('message is not a proxied message!')

    assert interaction.channel is not None
    assert interaction.guild is not None

    try:
        await get_proxy_webhook(interaction.channel)
    except Forbidden:
        raise InteractionError('bot does not access to this channel')

    db_message = await DBMessage.find_one({'proxy_id': message.id})

    if db_message is None:
        raise InteractionError(
            'message could not be found, is it more than a day old?')

    if interaction.author_id != db_message.author_id:
        raise InteractionError('you can only edit your own messages!')

    await interaction.response.send_modal(
        modal_plural_edit.with_text_kwargs(
            0, value=message.content
        ).with_extra(
            message
        )
    )


@slash_command(
    name='autoproxy',
    description='automatically proxy messages. leave empty to toggle',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='enabled',
            description='enable or disable auto proxying',
            required=False
        ),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='set to a specific member immediately',
            required=False,
            autocomplete=True
        ),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='server_only',
            description='whether to enable/disable in every server or just this one',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='fronting_mode',
            description='when enabled, using proxy tags will NOT auto switch (default: Unset / False)',
            required=False)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_autoproxy(
    interaction: Interaction,
    enabled: bool | None = None,
    member: ProxyMember | None = None,
    server_only: bool = True,
    fronting_mode: bool | None = None
) -> None:
    if interaction.guild is None and server_only:
        raise InteractionError(
            'you must use this command in a server when the `server_only` option is enabled')

    latch = (
        await Latch.find_one(
            {
                'user': interaction.author_id,
                'guild': interaction.guild_id if server_only else None
            }
        ) or await Latch(
            user=interaction.author_id,
            guild=interaction.guild_id if server_only else None,
            enabled=False,
            fronting=fronting_mode or False,
            member=None
        ).save()
    )

    latch.enabled = bool(
        enabled
        if enabled is not None else
        member or not latch.enabled
    )

    if member is not None:
        latch.member = member.id

    if not latch.enabled:
        latch.member = None

    if fronting_mode is not None:
        latch.fronting = fronting_mode

    message = (
        f'autoproxying in `{interaction.guild.name}` is now '
        if server_only and interaction.guild is not None else
        'global autoproxy is now '
    ) + (
        'enabled' if latch.enabled else 'disabled'
    )

    if latch.enabled:
        message += ' and set to ' + (
            f'member `{member.name}`'
            if member else
            'the next member to send a message'
        )

    await gather(
        latch.save(),
        interaction.response.send_message(
            embeds=[Embed.success(message)]
        )
    )


@slash_command(
    name='switch',
    description='quickly switch global autoproxy',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to switch to',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='enabled',
            description='enable or disable auto proxying',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='fronting_mode',
            description='when enabled, using proxy tags will NOT auto switch (default: Unset / False)',
            required=False)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_switch(
    interaction: Interaction,
    member: ProxyMember,
    enabled: bool | None = None,
    fronting_mode: bool | None = None
) -> None:
    assert slash_autoproxy.callback is not None
    await slash_autoproxy.callback(
        interaction,
        enabled=enabled,
        member=member,
        server_only=False,
        fronting_mode=fronting_mode
    )


@slash_command(
    name='delete_all_data',
    description='delete all of your data',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_delete_all_data(interaction: Interaction) -> None:
    await interaction.response.send_message(
        embeds=[Embed(
            title='are you sure?',
            description='this will delete all of your data, including groups, members, avatars, latches, and messages\n\nthis action is irreversible',
            color=0xff6969
        ).set_footer('click Dismiss Message to cancel')],
        components=[ActionRow(components=[button_delete_all_data])]
    )


@slash_command(
    name='reproxy',
    description='reproxy your last message. must be the last message in the channel',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to reproxy as',
            required=True,
            autocomplete=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_reproxy(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    assert interaction.channel is not None
    assert interaction.app_permissions is not None

    if interaction.channel.last_message_id is None:
        raise InteractionError('no message found')

    message = await Message.fetch(
        interaction.channel.id,
        interaction.channel.last_message_id,
        include_content=True
    )

    last_proxy_message = await DBMessage.find_one(
        {
            'author_id': interaction.author_id,
            'proxy_id': message.id
        },
        sort=[('ts', -1)]
    )

    if last_proxy_message is None:
        raise InteractionError(
            'no messages found, you cannot reproxy a message that was not the most recent message, or a message older than one day')

    message.author = (
        interaction.member.user
        if interaction.member is not None
        else interaction.user
    )

    message.channel = interaction.channel
    message.guild = interaction.guild

    await gather(
        process_proxy(
            message,
            member=member),
        interaction.response.send_message(
            embeds=[Embed.success(f'message reproxied as {member.name}')]),
        last_proxy_message.delete()
    )


@message_command(
    name='/plu/ral debug',
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def message_plural_debug(interaction: Interaction, message: Message) -> None:
    debug_log: list[DebugMessage | str] = [DebugMessage.ENABLER]

    try:
        await message.populate()
    except Forbidden:
        debug_log.append(DebugMessage.PERM_VIEW_CHANNEL)
    else:
        await process_proxy(message, debug_log, interaction.app_permissions)

    debug_log.remove(DebugMessage.ENABLER)

    if not debug_log:
        raise PluralException(
            'no debug messages generated\nthis should never happen and is a bug')

    await interaction.response.send_message(
        embeds=[Embed(
            title='debug log',
            description=f'```{'\n'.join(debug_log)}```',
            color=(
                0x69ff69
                if DebugMessage.SUCCESS in debug_log else
                0xff6969
            )
        )]
    )


@message_command(
    name='/plu/ral proxy info',
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def message_plural_proxy_info(interaction: Interaction, message: Message) -> None:
    if (
        message.author is None or
        message.webhook_id is None and
        message.interaction_metadata is None and
        not message.author.bot
    ):
        raise InteractionError('message is not a proxied message!')

    db_message = await DBMessage.find_one({'proxy_id': message.id})

    if db_message is None:
        raise InteractionError(
            'message could not be found, is it more than a day old?')

    embed = Embed(
        title='proxy info',
        color=0x69ff69
    )

    embed.add_field(
        name='author',
        value=f'<@{db_message.author_id}>',
        inline=False
    )

    embed.add_field(
        name='reason',
        value=db_message.reason,
        inline=False
    )

    embed.set_footer(
        text=f'original message id: {
            db_message.original_id or 'sent through /plu/ral api'}'
    )

    embed.set_thumbnail(
        url=message.author.avatar_url
    )

    await interaction.response.send_message(
        embeds=[embed]
    )


@slash_command(
    name='api',
    description='get or refresh an api key',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_api(interaction: Interaction) -> None:
    await interaction.response.send_message(
        embeds=[Embed(
            title='api key management',
            description=f'i\'ll put something here eventually, for now it\'s just a token reset portal\n{
                project.api_url}/docs',
            color=0x69ff69)],
        components=[ActionRow(components=[button_api_key])]
    )


# ! implement cooldowns
@slash_command(
    name='export',
    description='export your data',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='format',
            description='export format (default: standard)',
            required=False,
            choices=[
                ApplicationCommandOptionChoice(
                    name='standard; contains minimum data required for import, relatively safe to share',
                    value='standard'
                ),
                ApplicationCommandOptionChoice(
                    name='full; contains complete data package, DO NOT SHARE',
                    value='full'
                )])],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_export(
    interaction: Interaction,
    format: str = 'standard'
) -> None:
    export = await PluralExport.from_account_id(interaction.author_id)

    if format == 'standard':
        export = export.to_standard()

    data = export.model_dump_json()

    message = await interaction.response.send_message(
        content='your data is ready',
        attachments=[File(
            BytesIO(data.encode()),
            f'plural_export_{format}.json'
        )]
    )
    await interaction.followup.send(
        message.attachments[0].url
    )


@slash_command(
    name='help',
    description='get started with the bot',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_help(interaction: Interaction) -> None:
    await interaction.response.send_message(
        embeds=[Embed(
            title='welcome to /plu/ral!',
            description='please select a category',
            color=0x69ff69)],
        components=help_components
    )


@slash_command(
    name='import',
    description='import data from /plu/ral, pluralkit, or tupperbox',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='file',
            description='file to import. 8MB max',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='file_url',
            description='url of your exported file. 8MB max',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_import(
    interaction: Interaction,
    file: Attachment | None = None,
    file_url: str | None = None
) -> None:
    if file is None and file_url is None:
        # ? zero-width spaces to stop discord stupid list formatting looking like shit in embeds
        embed = Embed(
            title='how to import data',
            color=0x69ff69)
        embed.add_field(
            name='pluralkit',
            value='\n'.join([
                '​1. start a DM with pluralkit (<@466378653216014359>)',
                '​2. send `pk;export` and copy the link it DMs you',
                '​3. use the `/import` command and paste the link to the `file_url` parameter']),
            inline=False)
        embed.add_field(
            name='tupperbox',
            value='\n'.join([
                '​1. start a DM with tupperbox (<@431544605209788416>)',
                '​2. send `tul!export` and copy the link it DMs you',
                '​3. use the `/import` command and paste the link to the `file_url` parameter']),
            inline=False)

        await interaction.response.send_message(
            embeds=[embed]
        )
        return

    url = file.url if file else file_url
    assert url is not None

    try:
        data = loads(await get_from_cdn(url))
    except Exception:
        raise InteractionError('failed to read file')

    for model in (PluralKitExport, PluralExport, TupperboxExport, StandardExport):
        try:
            export = model.model_validate(data)
            break
        except ValidationError as e:
            continue
    else:
        raise InteractionError(
            'invalid export format; if you believe this is a bug, please send a message in the support server')

    if not isinstance(export, StandardExport):
        export = export.to_standard()

    await interaction.response.defer()

    logs = [
        log.lstrip('E: ')
        for log in await export.to_plural().import_to_account(interaction.author_id)
        if log.startswith('E: ')
    ]

    formatted_logs = f'```{'\n'.join(logs)}```'

    embed_message = (
        formatted_logs
        if len(formatted_logs) <= 4096 else
        'too many logs, sending as a file'
    )

    await interaction.followup.send(
        embeds=(
            [Embed.error(
                title='import failed',
                message=embed_message)]
            if LogMessage.NOTHING_IMPORTED.lstrip('E: ') in logs else
            [Embed.warning(
                title='import successful, but with errors',
                message=embed_message)]
            if logs else
            [Embed.success('import successful; no errors')]
        )
    )

    if len(formatted_logs) > 4096:
        message = await interaction.followup.send(
            content='import logs',
            attachments=[File(
                BytesIO(formatted_logs.encode()),
                'import_logs.txt'
            )]
        )
        await interaction.followup.send(
            message.attachments[0].url
        )


@slash_command(
    name='version',
    description='get the bot version and list of recent changes',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_version(interaction: Interaction) -> None:
    await interaction.response.send_message(
        embeds=[Embed(
            title=f'/plu/ral {VERSION}',
            description='\n'.join(LAST_TEN_COMMITS),
            color=0x69ff69
        )]
    )


@slash_command(
    name='edit',
    description='edit your last message (edit others by right clicking the message > Apps > /plu/ral edit)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='sed',
            description='skip the pop up and use sed editing (s/match/replace)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_edit(
    interaction: Interaction,
    sed: str | None = None
) -> None:
    userproxy_interaction, db_message = await UserProxyInteraction.find_one({
        'author_id': interaction.author_id,
        'channel_id': interaction.channel_id},
        sort=[('ts', -1)]
    ), await DBMessage.find_one(
        {
            'author_id': interaction.author_id,
            'channel_id': interaction.channel_id
        },
        sort=[('ts', -1)]
    )

    if userproxy_interaction is None and db_message is None:
        raise InteractionError('no messages found')

    if userproxy_interaction and db_message:
        obj = (
            userproxy_interaction
            if userproxy_interaction.ts > db_message.ts else
            db_message
        )
    else:
        obj = userproxy_interaction or db_message
        assert obj is not None

    match obj:
        case UserProxyInteraction():
            webhook = Webhook.from_proxy_interaction(obj)
            message = await webhook.fetch_message('@original')

            if not sed:
                assert message.author is not None

                await interaction.response.send_modal(
                    modal=umodal_edit.with_title(
                        'edit message'
                    ).with_text_kwargs(
                        0, value=message.content
                    ).with_extra(
                        message.id,
                        message.author.id
                    ))
                return

            content, embed = await _sed_edit(message, sed)

        case DBMessage():
            if interaction.channel is None:
                raise InteractionError('channel not found')

            message = await interaction.channel.fetch_message(
                obj.proxy_id,
                include_content=True
            )

            assert message.channel is not None
            assert message.author is not None

            if not sed:
                assert message_plural_edit.callback is not None
                await message_plural_edit.callback(interaction, message)
                return

            webhook = await get_proxy_webhook(message.channel)
            content, embed = await _sed_edit(message, sed)

            if (
                message.webhook_id is None and
                (member := await ProxyMember.find_one({'userproxy.bot_id': message.author.id})) and
                member.userproxy is not None and
                member.userproxy.token is not None
            ):
                await gather(
                    interaction.response.send_message(embeds=[embed]),
                    message.edit(content=content, token=member.userproxy.token))
                return

    await gather(
        interaction.response.send_message(embeds=[embed]),
        webhook.edit_message(
            message.id,
            content=content
        )
    )


@slash_command(
    name='config',
    description='configure your user settings',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='reply_format',
            description='the format for your replies (default: inline)',
            choices=[
                ApplicationCommandOptionChoice(
                    name='inline; placed at the top of your message',
                    value=str(ReplyFormat.INLINE.value)),
                ApplicationCommandOptionChoice(
                    name='embed; sent as an embed at the bottom of your message',
                    value=str(ReplyFormat.EMBED.value))],
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy_reply_format',
            description='the format for userproxy replies (default: inline)',
            choices=[
                ApplicationCommandOptionChoice(
                    name='none; reply only included in command (not visible on mobile)',
                    value=str(ReplyFormat.INLINE.value)),
                ApplicationCommandOptionChoice(
                    name='inline; placed at the top of the message',
                    value=str(ReplyFormat.INLINE.value)),
                ApplicationCommandOptionChoice(
                    name='embed; sent as an embed at the bottom of the message',
                    value=str(ReplyFormat.EMBED.value))],
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='userproxy_ping_replies',
            description='whether to ping when you reply to someone (only supports inline format) (default: False)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_config(
    interaction: Interaction,
    reply_format: str | None = None,
    userproxy_reply_format: str | None = None,
    userproxy_ping_replies: bool | None = None
) -> None:
    config = await UserConfig.get(interaction.author_id)

    if config is None:
        config = await UserConfig(
            id=interaction.author_id
        ).save()

    if all(
        option is None
        for option in {
            reply_format, userproxy_reply_format, userproxy_ping_replies}
    ):
        await interaction.response.send_message(
            embeds=[Embed(
                title='user configuration',
                description='please select a setting to configure',
                color=0x69ff69,
                fields=[
                    EmbedField(
                        name='reply format',
                        value=config.reply_format.name.lower(),
                        inline=False
                    )
                ])
            ])
        return

    changes = []

    if reply_format is not None:
        config.reply_format = ReplyFormat(int(reply_format))
        changes.append(
            f'reply format is now {config.reply_format.name.lower()}')

    if userproxy_reply_format is not None:
        config.userproxy_reply_format = ReplyFormat(
            int(userproxy_reply_format))
        changes.append(
            f'userproxy reply format is now {config.userproxy_reply_format.name.lower()}')

    if userproxy_ping_replies is not None:
        config.userproxy_ping_replies = userproxy_ping_replies
        changes.append(
            f'ping replies is now {"enabled" if config.userproxy_ping_replies else "disabled"}')

    await config.save_changes()

    await interaction.response.send_message(
        embeds=[Embed.success(
            '\n'.join(changes)
        )]
    )


@slash_command(
    name='serverconfig',
    description='configure /plu/ral\'s server settings',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='logclean',
            description='whether to enable log cleaning',
            required=False)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL],
    default_member_permissions=Permission.MANAGE_GUILD)
async def slash_serverconfig(
    interaction: Interaction,
    logclean: bool | None = None
) -> None:
    #! make this more versatile if you add more config
    assert interaction.guild_id is not None

    config = await GuildConfig.get(interaction.guild_id)

    if config is None:
        config = await GuildConfig(
            id=interaction.guild_id
        ).save()

    if all(
        option is None
        for option in {logclean}
    ):
        await interaction.response.send_message(
            embeds=[Embed(
                title='server configuration',
                description='please select a setting to configure',
                color=0x69ff69,
                fields=[
                    EmbedField(
                        name='log cleaning',
                        value='enabled' if config.logclean else 'disabled',
                        inline=False
                    )
                ])
            ])
        return

    if logclean is not None:
        config.logclean = logclean

    await config.save_changes()

    await interaction.response.send_message(
        embeds=[Embed.success(
            f'log cleaning is now {'enabled' if config.logclean else 'disabled'}'
        )]
    )
