from src.discord import slash_command, Interaction, message_command, InteractionContextType, Message, ApplicationCommandOption, ApplicationCommandOptionType, Embed, Permission, ApplicationIntegrationType, ApplicationCommandOptionChoice, Attachment, File, ActionRow
from src.components import modal_plural_edit, umodal_edit, button_api_key, help_components, button_delete_all_data
from src.porting import StandardExport, PluralExport, PluralKitExport, TupperboxExport, LogMessage
from src.db import Message as DBMessage, ProxyMember, Latch, UserProxyInteraction
from src.errors import InteractionError, Forbidden, PluralException
from src.logic.proxy import get_proxy_webhook, process_proxy
from src.discord.http import get_from_cdn
from pydantic_core import ValidationError
from src.models import DebugMessage
from src.models import project
from asyncio import gather
from orjson import loads
from io import BytesIO
from time import time


@slash_command(
    name='ping', description='check the bot\'s latency',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_ping(interaction: Interaction) -> None:
    timestamp = (interaction.id >> 22) + 1420070400000

    await interaction.response.send_message(
        f'pong! ({round((time()*1000-timestamp))}ms)'
    )


async def _userproxy_edit(interaction: Interaction, message: Message) -> bool:
    if message.interaction_metadata is None or message.webhook_id is None:
        return False

    if message.interaction_metadata.user.id != interaction.author_id:
        raise InteractionError('you can only edit your own messages!')

    if await ProxyMember.find_one({'userproxy.bot_id': message.webhook_id}) is None:
        raise InteractionError('message is not a proxied message!')

    if not await UserProxyInteraction.find_one({'message_id': message.id}):
        raise InteractionError(
            'due to discord limitations, you can\'t edit userproxy messages older than 15 minutes')

    await interaction.response.send_modal(
        modal=umodal_edit.with_title(
            'edit message'
        ).with_text_kwargs(
            0, value=message.content
        ).with_extra(
            message.id
        ))
    return True


@message_command(
    name='/plu/ral edit',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def message_plural_edit(interaction: Interaction, message: Message) -> None:
    assert interaction.channel is not None
    assert interaction.guild is not None

    if await _userproxy_edit(interaction, message):
        return

    if message.webhook_id is None:
        raise InteractionError('message is not a proxied message!')

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
        modal_plural_edit.with_extra(
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
            required=False)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_autoproxy(
    interaction: Interaction,
    enabled: bool | None = None,
    member: ProxyMember | None = None,
    server_only: bool = True
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
            required=False)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_switch(
    interaction: Interaction,
    member: ProxyMember,
    enabled: bool | None = None
) -> None:
    assert slash_autoproxy.callback is not None
    await slash_autoproxy.callback(
        interaction,
        enabled=enabled,
        member=member,
        server_only=False
    )


@slash_command(
    name='delete_all_data',
    description='delete all of your data',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_delete_all_data(interaction: Interaction) -> None:
    await interaction.response.send_message(
        embeds=[Embed(  # ! implement components, probably make view class
            title='are you sure?',
            description='this will delete all of your data, including groups, members, avatars, latches, and messages\n\nthis action is irreversible',
            color=0xff6969
        )],
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

    if not interaction.app_permissions & Permission.READ_MESSAGE_HISTORY:
        raise InteractionError(
            'bot does not have permission to read message history in this channel')

    messages = await interaction.channel.fetch_messages(limit=1)

    if not messages:
        raise InteractionError('message not found')

    message = messages[0]

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
    if message.webhook_id is None:
        raise InteractionError('message is not a proxied message!')

    assert message.author is not None

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

    embed.set_footer(
        text=f'original message id: {
            db_message.original_id or 'sent through / plu/ral api'}'
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
        raise InteractionError('help embed not implemented')

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

    print(export.model_dump_json())

    await interaction.response.defer()

    logs = [
        log.lstrip('E: ')
        for log in await export.to_plural().import_to_account(interaction.author_id)
        if log.startswith('E: ')
    ]

    print('\n'.join(logs))

    await interaction.followup.send(
        embeds=(
            [Embed.error(
                title='import failed',
                message=f'```{'\n'.join(logs)}```')]
            if LogMessage.NOTHING_IMPORTED.lstrip('E: ') in logs else
            [Embed.warning(
                title='import successful, but with errors',
                message=f'```{'\n'.join(logs)}```')]
            if logs else
            [Embed.success('import successful; no errors')]
        )
    )
