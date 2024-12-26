from src.discord import slash_command, message_command, Interaction, ApplicationCommandScope, Attachment, MessageFlag, ApplicationCommandOption, ApplicationCommandOptionType, Message, Embed, Permission, ApplicationIntegrationType, InteractionContextType, Webhook, AllowedMentions
from regex import match as regex_match, sub, error as RegexError, IGNORECASE, escape  # noqa: N812
from src.db import Reply, UserProxyInteraction, ReplyFormat, UserConfig, ReplyType
from src.components.userproxy import umodal_send, umodal_edit
from src.errors import InteractionError, NotFound
from datetime import datetime, timedelta, UTC
from src.logic.proxy import format_reply
from src.models import project
from asyncio import gather


SED_PATTERN = r'^s/(.*?)/(.*?)/?([gi]*)$'


async def _sed_edit(
    interaction: Interaction,
    message: str
) -> bool:
    match = regex_match(SED_PATTERN, message)

    if not match:
        return False

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

    userproxy_interaction = await UserProxyInteraction.find_one(
        {
            'author_id': interaction.author_id,
            'channel_id': interaction.channel_id
        },
        sort=[('ts', -1)]
    )

    if userproxy_interaction is None:
        raise InteractionError(
            'no message found; messages older than 15 minutes cannot be edited')

    webhook = Webhook.from_proxy_interaction(
        userproxy_interaction
    )

    try:
        original_message = await webhook.fetch_message('@original')
    except NotFound:
        raise InteractionError(
            'original message not found; message may have been deleted'
        ) from None

    try:
        edited_content = sub(
            escape(expression), replacement, original_message.content, count=count, flags=flags)
    except RegexError:
        raise InteractionError('invalid regular expression') from None

    embed = (
        Embed.success('message edited')
        if edited_content != original_message.content else
        Embed.warning('no changes were made')
    )

    embed.set_footer(text=f'message id: {original_message.id}')

    gather(
        webhook.edit_message(
            '@original',
            content=edited_content),
        interaction.response.send_message(embeds=[embed])
    )

    return True


async def _external_app_check(
    interaction: Interaction
) -> bool:
    if (
        interaction.member and
        interaction.member.permissions and
        not interaction.member.permissions & Permission.USE_EXTERNAL_APPS
    ):
        await interaction.response.send_message(
            embeds=[Embed.error(
                'you do not have permission to use external apps in this server; please contact a moderator')
            ]
        )
        return True
    return False


@slash_command(
    name='proxy',
    description='send a message',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='message',
            min_length=0,
            max_length=2000,
            description='message to send',
            required=False
        ),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='queue_for_reply',
            description='queue for reply',
            required=False
        )]+[ApplicationCommandOption(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name=f'attachment{i}' if i else 'attachment',
            description='send an attachment',
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
    if await _external_app_check(interaction):
        return

    attachments = list(_attachments.values())
    if not message and not attachments:
        await interaction.response.send_modal(
            modal=umodal_send.with_title(
                'proxy a message'
            ).with_text_kwargs(
                0, placeholder='you should only use this if you need to send a message with newlines'
            ).with_extra(
                queue_for_reply
            )
        )
        return

    if message and await _sed_edit(interaction, message):
        return

    if attachments:
        assert interaction.app_permissions is not None
        if not interaction.app_permissions & Permission.ATTACH_FILES:
            raise InteractionError(
                'bot does not have permission to attach files in this channel')

        limit = interaction.guild.filesize_limit if interaction.guild is not None else 26_214_400

        if sum(attachment.size for attachment in attachments) > limit:
            raise InteractionError(
                f'attachments exceed the {limit / 1024 / 1024}MB limit')

        if not queue_for_reply:
            await interaction.response.defer(MessageFlag.NONE)

    sender = (
        interaction.followup.send
        if interaction.response.responded else
        interaction.response.send_message
    )

    if not queue_for_reply:
        sent_message = await sender(
            content=message,
            attachments=[await attachment.as_file() for attachment in attachments],
            flags=MessageFlag.NONE
        )

        await UserProxyInteraction(
            author_id=interaction.author_id,
            application_id=interaction.application_id,
            message_id=sent_message.id,
            channel_id=sent_message.channel_id,
            token=interaction.token
        ).save()
        return

    await Reply(
        type=ReplyType.QUEUE,
        bot_id=int(interaction.application_id),
        channel=int(interaction.channel_id or 0),
        content=message,
        attachments=[
            Reply.Attachment(
                url=attachment.url,
                filename=attachment.filename,
                description=attachment.description or None)
            for attachment in attachments],
        message_id=None,
        author=None
    ).save()

    await sender(
        embeds=[
            Embed.success(
                title='message queued for reply',
                message='use the reply command within the next 5 minutes to send your message'
            )
        ],
    )


@message_command(
    name='reply',
    scope=ApplicationCommandScope.USERPROXY,
    contexts=InteractionContextType.ALL(),
    integration_types=[ApplicationIntegrationType.USER_INSTALL])
async def umessage_reply(
    interaction: Interaction,
    message: Message
) -> None:
    if await _external_app_check(interaction):
        return

    reply = await Reply.find_one({
        'bot_id': int(interaction.application_id),
        'channel': int(interaction.channel_id or 0),
        'type': ReplyType.QUEUE
    })

    title = f'reply to {message.author.username if message.author else 'a message'}'

    if len(title) > 45:
        title = 'reply to a message'

    if reply is None:
        assert message.author is not None
        await Reply(
            type=ReplyType.REPLY,
            bot_id=int(interaction.application_id),
            channel=int(interaction.channel_id or 0),
            content=message.content or '',
            attachments=[Reply.Attachment(
                url='',
                filename='',
                description=''
            )] if message.attachments else [],
            message_id=message.id,
            author=Reply.Author(
                id=message.author.id,
                username=message.author.username,
                avatar=message.author.avatar),
            # ? replies are stored for 15 minutes
            ts=datetime.now(UTC) + timedelta(minutes=10)
        ).save()

        await interaction.response.send_modal(
            modal=umodal_send.with_title(
                title
            ).with_extra(
                False
            ))
        return

    attachments = [
        await attachment.as_file()
        for attachment in reply.attachments
    ]

    if attachments:
        await interaction.response.defer(MessageFlag.NONE)

    proxy_content = reply.content

    user_config = await UserConfig.get(interaction.author_id) or UserConfig.default()

    reply_format = (
        user_config.dm_reply_format
        if interaction.is_dm else
        user_config.reply_format
    )

    proxy_with_reply, reply_mentions = format_reply(
        reply.content or '',
        message,
        reply_format
    )

    if isinstance(proxy_with_reply, str):
        proxy_content = proxy_with_reply

    mentions = AllowedMentions.parse_content(
        proxy_content or '').strip_mentions(reply_mentions)

    if (
        mentions.users and
        message.author and
        message.author.id in mentions.users
    ) and not (
        reply_format == ReplyFormat.INLINE and
        user_config.userproxy_ping_replies
    ):
        mentions.users.remove(message.author.id)

    sent_message = await interaction.send(
        content=proxy_content or None,
        attachments=attachments,
        embeds=[proxy_with_reply] if isinstance(
            proxy_with_reply, Embed) else None,
        allowed_mentions=mentions,
        flags=MessageFlag.NONE
    )

    await reply.delete()

    await UserProxyInteraction(
        author_id=interaction.author_id,
        application_id=interaction.application_id,
        message_id=sent_message.id,
        channel_id=sent_message.channel_id,
        token=interaction.token
    ).save()


@message_command(
    name='edit',
    scope=ApplicationCommandScope.USERPROXY,
    contexts=InteractionContextType.ALL(),
    integration_types=[ApplicationIntegrationType.USER_INSTALL])
async def umessage_edit(
    interaction: Interaction,
    message: Message
) -> None:
    assert message.author is not None

    userproxy_interaction = await UserProxyInteraction.find_one({
        'message_id': message.id
    })

    if userproxy_interaction is None:
        raise InteractionError(
            'message not found\ndue to discord limitations, you can\'t edit messages that are older than 15 minutes')

    if userproxy_interaction.application_id != interaction.application_id != message.webhook_id:
        raise InteractionError('you can only edit your own messages!')

    await interaction.response.send_modal(
        modal=umodal_edit.with_title(
            'edit message'
        ).with_text_kwargs(
            0, value=message.content
        ).with_extra(
            message.id,
            message.author.id
        )
    )

    await interaction.followup.send(
        embeds=[
            Embed.warning(
                title='deprecation warning',
                message='\n\n'.join([
                    'userproxy edit command is deprecated and will be removed in the future',
                    'please add /plu/ral as a user app to edit messages',
                    f'you can add /plu/ral by clicking [here](https://discord.com/oauth2/authorize?client_id={project.application_id})',
                    'once you have added /plu/ral, you can run /member userproxy sync to remove this command'
                ])
            )
        ]
    )
