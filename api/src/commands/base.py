from __future__ import annotations

from datetime import datetime, timedelta, UTC
from urllib.parse import urlparse
from asyncio import gather
from io import BytesIO

from pydantic import ValidationError
from beanie import PydanticObjectId
from orjson import loads, dumps

from plural.db.enums import AutoProxyMode, SupporterTier, ShareType
from plural.db.usergroup import AvatarOnlyGroup, AvatarOnlyMember
from plural.errors import InteractionError, NotFound
from plural.missing import MISSING
from plural.otel import inject, cx
from plural.db import (
    Message as DBMessage,
    ProxyMember,
    AutoProxy,
    Usergroup,
    Group,
    Share,
    redis
)

from src.core.version import VERSION, LAST_TEN_COMMITS
from src.core.http import File, GENERAL_SESSION
from src.core.models import env
from src.discord import (
    ApplicationCommandOptionType,
    ApplicationIntegrationType,
    InteractionContextType,
    ApplicationCommand,
    SlashCommandGroup,
    message_command,
    slash_command,
    Interaction,
    Attachment,
    Message,
    Embed,
    User
)

from src.components import PAGES
from src.porting import (
    Standardv1Export,
    TupperboxExport,
    PluralKitExport,
    StandardExport,
    PluralExport
)

from .helpers import (
    timestring_to_timedelta,
    make_json_safe,
    sed_edit
)


account = SlashCommandGroup(
    name='account',
    description='Share your account',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL()
)


@message_command(
    name='/plu/ral debug',
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def message_plural_debug(
    interaction: Interaction,
    message: Message
) -> None:
    debug_log_str = await redis.hget('proxy_debug', str(message.id))

    if debug_log_str is None:
        raise InteractionError('No debug log found for this message')

    debug_log: list[str] = loads(debug_log_str)

    if (
        debug_log[0] != str(interaction.author_id) and
        interaction.author_id not in env.admins
    ):
        raise InteractionError(
            'You can only view the debug logs of your own messages'
        )

    success = (
        debug_log[-1].startswith('Latency: ') or
        debug_log[1] == 'Reproxy command used.'
    )

    await interaction.response.send_message(embeds=[Embed(
        title='debug log',
        description=f'```{'\n'.join(debug_log[1:])}```',
        color=(
            0x69ff69
            if success else
            0xff6969
        )
    )])


@message_command(
    name='/plu/ral edit',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def message_plural_edit(
    interaction: Interaction,
    message: Message
) -> None:
    await PAGES['edit'](interaction, message)


@message_command(
    name='/plu/ral proxy info',
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def message_plural_proxy_info(
    interaction: Interaction,
    message: Message
) -> None:
    #! do sp integration at some point
    db_message = await DBMessage.find_one({
        'proxy_id': message.id
    })

    if db_message is None:
        raise InteractionError('No proxy info found for this message')

    member = await ProxyMember.get(db_message.member_id)

    if member is None:
        raise InteractionError('Member not found')

    usergroup = await Usergroup.get_by_user(db_message.author_id)

    embed = Embed(
        title='Proxy Info',
        color=0x69ff69
    ).add_field(
        name='Author',
        value=f'<@{db_message.author_id}>',
        inline=False
    ).add_field(
        name='Proxy Reason',
        value=db_message.reason,
        inline=False
    ).set_footer(
        'original message id: ' + (
            db_message.original_id or
            'None (Userproxy command)'
            if db_message.reason.startswith('Userproxy') else
            'sent through /plu/ral api')
    ).set_thumbnail(
        message.author.avatar_url
    )

    if usergroup.data.supporter_tier == SupporterTier.SUPPORTER:
        embed.fields[0].value = f'🌟{embed.fields[0].value}🌟'
        embed.footer.text += '\n🌟/plu/ral supporter🌟'

    await interaction.response.send_message(
        embeds=[embed]
    )


@account.command(
    name='accept',
    description='Join a usergroup',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.USER,
            name='user',
            description='User who invited you',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_account_accept(
    interaction: Interaction,
    user: User
) -> None:
    share = await Share.find_one({
        'type': ShareType.USERGROUP,
        'sharer': user.id,
        'sharee': interaction.author_id
    })

    if share is None:
        raise InteractionError(
            f'<@{user.id}> did not share their account with you.'
        )

    sharer = await Usergroup.get_by_user(user.id)
    sharee = await Usergroup.get_by_user(interaction.author_id)

    if sharer.id == sharee.id:
        raise InteractionError(
            f'You and <@{user.id}> are already in the same usergroup.'
        )

    existing_groups = await Group.find({
        '$or': [{'accounts': sharee.id}]
    }).to_list()

    if existing_groups:
        raise InteractionError(
            'You cannot join a usergroup with existing data\n\n'
            'Use the {cmd_ref[delete_all_data]} command to delete your data'
        )

    sharer.users.add(interaction.author_id)

    await gather(
        sharer.save(),
        sharee.delete(),
        share.delete(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'Joined account with <@{user.id}>'
            )]
        )
    )


@account.command(
    name='share',
    description='Create a usergroup',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.USER,
            name='user',
            description='User to share with',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_account_share(
    interaction: Interaction,
    user: User
) -> None:
    if user.id == interaction.author_id:
        raise InteractionError('You cannot share a group with yourself.')

    share = await Share.find_one({
        'type': ShareType.USERGROUP,
        'sharer': interaction.author_id,
        'sharee': user.id
    })

    if share is not None:
        raise InteractionError(
            'You can only have one pending account share per user.'
        )

    sharer = await Usergroup.get_by_user(interaction.author_id)
    sharee = await Usergroup.get_by_user(user.id)

    if sharer.id == sharee.id:
        raise InteractionError(
            f'You and <@{user.id}> are already in the same usergroup.'
        )

    await gather(
        Share(
            type=ShareType.USERGROUP,
            sharer=interaction.author_id,
            sharee=user.id,
            group=None,
            permission_level=None
        ).save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'Shared account with <@{user.id}>\n\n'
                'They can accept by running {cmd_ref[account accept]} '
                'within the next 6 hours\n\nNote: '
                'The account you\'re sharing with must have no data',
                insert_command_ref=True
            )]
        )
    )


@slash_command(
    name='api',
    description='Create and manage your /plu/ral integrations',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_api(
    interaction: Interaction  # noqa: ARG001
) -> None:
    raise InteractionError(
        'API will be implemented in the future I just need v3 out now'
    )


@slash_command(
    name='autoproxy',
    description='Automatically proxy messages. Leave empty to toggle',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='enable',
            description='Enable or disable autoproxy',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Set to a specific member immediately',
            required=False,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='global',
            description='Whether to proxy everywhere or just in this server; Default is False',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='mode',
            description='Default: `Latch`',
            choices=[
                ApplicationCommand.Option.Choice(
                    name='Front; using proxy tags will NOT switch the autoproxied member',
                    value='front'),
                ApplicationCommand.Option.Choice(
                    name='Latch; using proxy tags WILL switch the autoproxied member',
                    value='latch'),
                ApplicationCommand.Option.Choice(
                    name='Locked; autoproxy will not switch even if you use proxy tags',
                    value='locked')],
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='expiry',
            description='Set expiry time (format: 1d2h3m4s); Default is None (never expires)',
            required=False)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_autoproxy(
    interaction: Interaction,
    enable: bool | None = None,
    member: ProxyMember | None = None,
    global_: bool = False,
    mode: str | None = None,
    expiry: str | None = None
) -> None:
    match (mode.lower() if mode else None):
        case 'front':
            mode = AutoProxyMode.FRONT
        case 'latch':
            mode = AutoProxyMode.LATCH
        case 'locked':
            mode = AutoProxyMode.LOCKED
        case None:
            mode = AutoProxyMode.LATCH
        case _:
            raise InteractionError(f'invalid mode `{mode}`')
    mode: AutoProxyMode

    autoproxy = await AutoProxy.find_one({
        'user': interaction.author_id,
        'guild': None if global_ else interaction.guild_id
    })

    if (
        autoproxy is not None and
        autoproxy.ts is not None and
        autoproxy.ts.replace(tzinfo=UTC) < datetime.now(UTC)
    ):
        # ? autoproxy has expired but mongo ttl hasn't run yet
        await autoproxy.delete()
        autoproxy = None

    if enable is False or (
        enable is None and
        member is None
    ):
        if autoproxy is None:
            raise InteractionError('Autoproxy is already disabled')

        await autoproxy.delete()

        embed = Embed.success(
            f'{'Global' if global_ else 'Server'} autoproxy disabled'
        )

        if not global_:
            embed.set_author(
                name=interaction.guild.name,
                icon_url=interaction.guild.icon_url or MISSING
            )

        if (
            await AutoProxy.find_one({
                'user': interaction.author_id,
                'guild': interaction.guild_id if global_ else None})
        ) is not None:
            embed.set_footer(
                text='WARNING: Your messages will still be proxied here since you' + (
                    'r server autoproxy is still enabled'
                    if global_ else
                    ' have a global autoproxy enabled'
                )
            )

        await interaction.send(embeds=[embed])
        return

    if enable is None:
        enable = autoproxy is None

    expiry_time = datetime.now(UTC) + (
        timestring_to_timedelta(expiry)
        if expiry else
        timedelta()
    )

    embed = Embed.success(
        f'{'Global' if global_ else 'Server'} autoproxy enabled'
    ).add_field(
        name='Member',
        value=(
            member.name
            if member else
            'Next'
        )
    ).add_field(
        name='Expires',
        value=(
            f'<t:{int(expiry_time.timestamp())}:R>'
            if expiry is not None
            else 'never'
        )
    ).add_field(
        name='Mode',
        value=mode.name.capitalize()
    )

    if not global_:
        embed.set_author(
            name=interaction.guild.name,
            icon_url=interaction.guild.icon_url or MISSING
        )

    tasks = [
        AutoProxy(
            user=interaction.author_id,
            guild=None if global_ else str(interaction.guild_id),
            mode=mode,
            member=member.id if member else None,
            ts=expiry_time if expiry is not None else None
        ).save(),
        interaction.response.send_message(
            embeds=[embed]
        )
    ]

    if autoproxy is not None:
        tasks.append(autoproxy.delete())

    await gather(*tasks)


@slash_command(
    name='config',
    description='Configure /plu/ral settings. Leave empty to use button menu',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='option',
            description='Config option; Use the autocomplete',
            required=False,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='value',
            description='Config value',
            required=False,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_config(
    interaction: Interaction,
    option: str | None = None,
    value: str | None = None  # noqa: ARG001
) -> None:
    if option is None:
        return await PAGES['home'](interaction)

    raise InteractionError(
        'Text-based config is not yet implemented\n\n'
        'Please use the button menu instead.'
    )


@slash_command(
    name='delete_all_data',
    description='Delete all of your data',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_delete_all_data(
    interaction: Interaction
) -> None:
    await PAGES['delete_all_data'](interaction)


@slash_command(
    name='edit',
    description='Edit your most recent message',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='sed',
            description='Use s/e/d editing. Leave empty to edit with pop up',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_edit(
    interaction: Interaction,
    sed: str | None = None
) -> None:
    db_message = await DBMessage.find_one(
        {
            'author_id': interaction.author_id,
            'channel_id': interaction.channel_id
        },
        sort=[('ts', -1)]
    )

    if db_message is None:
        raise InteractionError('No messages found to edit')

    message = await Message.fetch(
        interaction.channel_id,
        db_message.proxy_id
    )

    if sed is None:
        await PAGES['edit'](interaction, message)
    else:
        await sed_edit(interaction, message, sed)


@slash_command(
    name='explain',
    description='Send a quick message explaining /plu/ral',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_explain(
    interaction: Interaction
) -> None:
    raise NotImplementedError


@slash_command(
    name='export',
    description='Export your data',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='format',
            description='Export format (default: Standard)',
            required=False,
            choices=[
                ApplicationCommand.Option.Choice(
                    name='Standard; Minimum data required for import, safe to share',
                    value='standard'),
                ApplicationCommand.Option.Choice(
                    name='Full; Complete data package. DO NOT SHARE. Cannot be used for import.',
                    value='full')])],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_export(
    interaction: Interaction,
    format: str = 'standard'
) -> None:
    export = await PluralExport.from_user_id(
        interaction.author_id,
        format
    )

    if format == 'standard':
        export = await export.to_standard()

    message = await interaction.response.send_message(
        content='Your data is ready',
        with_response=True,
        attachments=[File(
            BytesIO(dumps(  # ? i miss elixir
                make_json_safe(export.model_dump()))),
            f'plural_{
                'export'
                if format == 'standard' else
                'data_package'
            }.json'
        )]
    )

    await interaction.followup.send(
        message.attachments[0].url
    )


@slash_command(
    name='help',
    description='Get started with the bot',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_help(
    interaction: Interaction
) -> None:
    await PAGES['help'](interaction, 'main')


@slash_command(
    name='import',
    description='Import data from /plu/ral, PluralKit, or Tupperbox',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='file_url',
            description='URL of your exported file. 4MB max',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='file',
            description='File to import. 4MB max',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_import(
    interaction: Interaction,
    file: Attachment | None = None,
    file_url: str | None = None
) -> None:
    if file is None and file_url is None:
        # ? zero-width spaces to stop discord list formatting looking like doo doo in embeds
        embed = Embed(
            title='How to import data',
            color=0x69ff69
        ).add_field(
            name='PluralKit',
            value=(
                '​1. Start a DM with PluralKit (<@466378653216014359>)\n'
                '​2. Send `pk;export` and copy the link it DMs you\n'
                '​3. Use the {cmd_ref[import]} command and paste the link to the `file_url` parameter'),
            inline=False,
            insert_command_ref=True
        ).add_field(
            name='Tupperbox',
            value=(
                '​1. Start a DM with Tupperbox (<@431544605209788416>)\n'
                '​2. Send `tul!export` and copy the link it DMs you\n'
                '​3. Use the {cmd_ref[import]} command and paste the link to the `file_url` parameter'),
            inline=False,
            insert_command_ref=True
        )

        await interaction.response.send_message(
            embeds=[embed])
        return

    if file_url:
        parsed = urlparse(file_url)

        if not parsed.hostname:
            raise InteractionError('Invalid URL')

        if parsed.hostname not in {'discord.com', 'cdn.discordapp.com'}:
            raise InteractionError('URL must be from Discord')

        if parsed.scheme != 'https':
            raise InteractionError('URL must be https')

    url = file.url if file else file_url
    assert url is not None

    await interaction.response.defer()

    async with GENERAL_SESSION.get(url) as response:
        if response.status != 200:
            raise InteractionError(
                'Failed to fetch file. Please make sure the url is correct.'
            )

        if int(response.content_length or 0) > env.max_avatar_size:
            raise InteractionError('File too large (4MB max)')

        data = bytearray()

        async for chunk in response.content.iter_chunked(16384):
            data.extend(chunk)

            if len(data) > env.max_avatar_size:
                raise InteractionError('File too large (4MB max)')

        try:
            json = loads(data)
        except Exception as e:
            raise InteractionError(
                'Invalid json data. Please make sure the file is correct.'
            ) from e

    for model in (TupperboxExport, PluralKitExport, StandardExport, Standardv1Export):
        try:
            export = model.model_validate(json)
        except ValidationError:
            continue

        break
    else:
        raise InteractionError('\n\n'.join([
            'Invalid data. Please make sure the file is correct.',
            'If it is, please report this issue in [the support server](https://discord.gg/4mteVXBDW7)'
        ]))

    cx().set_attribute(
        'import.source.name',
        export.__class__.__name__.rstrip('Export').lower()
    )

    export = export.to_standard()

    logs = await export.do_import(
        interaction.author_id,
        dry_run=True
    )

    cx().set_attribute(
        'import.logs',
        logs
    )

    # ? intentionally running the import again in case user data has changed
    if not logs:
        await export.do_import(interaction.author_id, False)

        await interaction.followup.send(embeds=[
            Embed.success(
                title='Import successful',
                message='No errors found'
            )
        ])

        return

    key = str(PydanticObjectId())

    pipeline = redis.pipeline()

    pipeline.json().set(
        f'pending_import:{key}',
        '$',
        export.model_dump(mode='json')
    )
    pipeline.expire(f'pending_import:{key}', timedelta(minutes=15))

    await pipeline.execute()

    await PAGES['import_confirm'](interaction, logs, key)


@slash_command(
    name='manage',
    description='Manage your groups and members',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_manage(
    _interaction: Interaction
) -> None:
    raise InteractionError('\n\n'.join([
        'Button-based group and member management is not yet implemented',
        'Please use the group and member commands instead'
    ]))


@slash_command(
    name='ping',
    description='Check the bot latency',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_ping(
    interaction: Interaction
) -> None:
    embed = Embed(
        title='Pong!',
        description=f'[more info about what these numbers mean](https://{env.domain}/guide/command-reference#ping)',
        color=0x69ff69
    )

    if (interaction_latency := await redis.lrange('interaction_latency', 0, -1)):
        embed.add_field(
            name='Interaction Latency',
            value=f'{round(sum(map(float, interaction_latency))/len(interaction_latency))}ms'
        )

    if (proxy_latency := await redis.lrange('proxy_latency', 0, -1)):
        embed.add_field(
            name='Proxy Latency',
            value=f'{round(sum(map(float, proxy_latency))/len(proxy_latency))}ms'
        )

    await interaction.response.send_message(embeds=[embed])


@slash_command(
    name='reproxy',
    description='Reproxy your last message. Must be the latest message in the channel',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to reproxy as',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_tag',
            description='Specify a proxy tag (uses proxy tag avatar)',
            required=False,
            autocomplete=True)],
    contexts=[InteractionContextType.GUILD],
    integration_types=[ApplicationIntegrationType.GUILD_INSTALL])
async def slash_reproxy(
    interaction: Interaction,
    member: ProxyMember,
    proxy_tag: int | None = None
) -> None:
    if not interaction.channel:
        raise InteractionError(
            'Current channel not found, this probably shouldn\'t happen'
        )

    if not interaction.channel.last_message_id:
        raise InteractionError(
            'No last message found in this channel'
        )

    debug_log = await redis.hget(
        'proxy_debug',
        str(interaction.channel.last_message_id)
    )

    if debug_log is None:
        raise InteractionError(
            'No debug log found for the last message in this channel. Reproxy must be within one hour of the original message'
        )

    if interaction.author_id != int(loads(debug_log)[0]):
        raise InteractionError(
            'You can only reproxy your own messages'
        )

    try:
        message = await Message.fetch(
            interaction.channel_id,
            interaction.channel.last_message_id)
    except NotFound as e:
        raise InteractionError(
            'Failed to fetch message. It may have been deleted'
        ) from e

    message_event = message._raw

    message_event['__plural_member'] = str(member.id)
    message_event['__plural_proxy_tag'] = proxy_tag
    message_event['__plural_traceparent'] = inject({}).get('traceparent')

    assert interaction.member is not None

    message_event['author'] = interaction.member.user._raw
    message_event['member'] = interaction.member._raw
    message_event['channel_type'] = interaction.channel.type.value
    message_event['guild_id'] = str(interaction.guild_id)

    message_event['member'].pop('user', None)
    message_event.pop('webhook_id', None)
    message_event.pop('application_id', None)

    await redis.xadd(
        'discord_events',
        {'data': dumps({
            't': 'MESSAGE_CREATE',
            'd': message_event
        })}
    )

    await interaction.response.send_message(
        content='Message reproxied successfully'
    )


@slash_command(
    name='stats',
    description='Get your /plu/ral stats',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_stats(
    interaction: Interaction
) -> None:
    usergroup = await Usergroup.get_by_user(interaction.author_id)

    groups = await Group.find({
        '$or': [
            {'accounts': usergroup.id},
            {'users': interaction.author_id}]
    }, projection_model=AvatarOnlyGroup).to_list()

    members = await ProxyMember.find({'_id': {'$in': list({
        member_id
        for group in groups
        for member_id in group.members
    })}}, projection_model=AvatarOnlyMember).to_list()

    avatars = {
        *[group.avatar for group in groups],
        *[member.avatar for member in members],
        *[
            tag.avatar
            for member in members
            for tag in member.proxy_tags
        ]
    }

    avatars.discard(None)

    await interaction.response.send_message(embeds=[
        Embed(
            title='Stats',
            color=0x69ff69,
            footer=(
                Embed.Footer(text='🌟/plu/ral supporter🌟')
                if usergroup.data.supporter_tier == SupporterTier.SUPPORTER
                else MISSING)
        ).add_field(
            'Groups',
            str(len(groups)),
            inline=False
        ).add_field(
            'Members',
            str(len(members)),
            inline=False
        ).add_field(
            'Avatars',
            f'{len(avatars)}/{usergroup.data.image_limit}',
            inline=False
        ).set_author(
            name=interaction.author.display_name,
            icon_url=interaction.author.avatar_url
        )
    ])


@slash_command(
    name='switch',
    description='Quickly set global autoproxy',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to switch to, or "off" to disable',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='mode',
            description='Default: `Latch`',
            choices=[
                ApplicationCommand.Option.Choice(
                    name='Front; Using proxy tags will NOT switch the autoproxied member',
                    value='front'),
                ApplicationCommand.Option.Choice(
                    name='Latch; Using proxy tags WILL switch the autoproxied member',
                    value='latch'),
                ApplicationCommand.Option.Choice(
                    name='Locked; Autoproxy will not switch even if you use proxy tags',
                    value='locked')],
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='expiry',
            description='Set expiry time (format: 1d2h3m4s); Default is None (never expires)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_switch(
    interaction: Interaction,
    member: ProxyMember | str,
    mode: str | None = None,
    expiry: str | None = None
) -> None:
    await slash_autoproxy.callback(
        interaction,
        enable=member != 'off',
        member=member if member != 'off' else None,
        global_=True,
        mode=mode,
        expiry=expiry
    )


@slash_command(
    name='version',
    description='Get bot version and list of recent changes',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_version(
    interaction: Interaction
) -> None:
    await interaction.response.send_message(
        embeds=[Embed(
            title=f'/plu/ral {VERSION}',
            description='\n'.join(LAST_TEN_COMMITS),
            color=0x69ff69
        )]
    )
