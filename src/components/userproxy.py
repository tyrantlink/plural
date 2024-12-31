from src.discord import modal, TextInput, Interaction, TextInputStyle, MessageFlag, Webhook, Embed, AllowedMentions, FakeMessage, User, Snowflake
from src.db import UserProxyInteraction, Reply, ProxyMember, ReplyType, UserConfig, ReplyFormat, DiscordCache
from src.errors import InteractionError, HTTPException
from src.logic.proxy import format_reply
from asyncio import gather


__all__ = (
    'umodal_edit',
    'umodal_send',
)


@modal(
    custom_id='umodal_send',
    text_inputs=[
        TextInput(
            custom_id='message',
            style=TextInputStyle.LONG,
            max_length=2000,
            label='message',
            required=True)])
async def umodal_send(
    interaction: Interaction,
    queue_for_reply: bool,
    reply_id: int | None = None,
    message: str = ''
) -> None:
    if queue_for_reply:
        await Reply(
            type=ReplyType.QUEUE,
            bot_id=int(interaction.application_id),
            channel=int(interaction.channel_id or 0),
            attachments=[],
            content=message,
            message_id=None,
            author=None
        ).save()

        await interaction.response.send_message(
            embeds=[
                Embed.success(
                    title='message queued for reply',
                    message='use the reply command within the next 5 minutes to send your message'
                )
            ]
        )

        return

    reply = await Reply.find_one({
        'bot_id': int(interaction.application_id),
        'channel': int(interaction.channel_id or 0),
        'type': ReplyType.REPLY,
        'message_id': reply_id
    })

    if reply is None:
        sent_message = await interaction.response.send_message(
            content=message,
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

    assert reply.author is not None

    enforce_format, channel_data = None, None

    if interaction.channel_id is not None:
        channel_data = await DiscordCache.get_channel(
            int(interaction.channel_id), guild_id=int(interaction.guild_id or 0))

        if channel_data is not None:
            enforce_format = channel_data.meta.get('enforce_format', None)

    user_config = await UserConfig.get(interaction.author_id) or UserConfig.default()

    reply_format = (
        ReplyFormat(enforce_format)
        if enforce_format is not None else (
            user_config.dm_reply_format
            if interaction.is_dm else
            user_config.reply_format
        )
    )

    proxy_content = message

    proxy_with_reply, reply_mentions = format_reply(
        proxy_content,
        FakeMessage(
            id=Snowflake(reply.message_id or 0),
            channel_id=int(interaction.channel_id or 0),
            content=reply.content or '',
            author=User(
                id=Snowflake(reply.author.id),
                discriminator='0000',
                username=reply.author.username,
                avatar=reply.author.avatar),
            guild=interaction.guild),
        reply_format
    )

    if isinstance(proxy_with_reply, str):
        proxy_content = proxy_with_reply

    mentions = AllowedMentions.parse_content(
        proxy_content or '').strip_mentions(reply_mentions)

    if (
        mentions.users and
        reply.author is not None and
        reply.author.id in mentions.users
    ) and not (
        reply_format == ReplyFormat.INLINE and
        user_config.userproxy_ping_replies
    ):
        mentions.users.remove(reply.author.id)

    _, sent_message = await gather(
        reply.delete(),
        interaction.send(
            content=proxy_content or None,
            embeds=[proxy_with_reply] if isinstance(
                proxy_with_reply, Embed) else None,
            allowed_mentions=mentions,
            flags=MessageFlag.NONE
        )
    )

    if not (
        interaction.guild is None or not sent_message.flags & MessageFlag.EPHEMERAL
    ):
        await interaction.send('automod blocked the reply; try again to send without reply formatting')

        if channel_data is not None:
            channel_data.meta['enforce_format'] = ReplyFormat.NONE.value
            await channel_data.save()

        return

    await UserProxyInteraction(
        author_id=interaction.author_id,
        application_id=interaction.application_id,
        message_id=sent_message.id,
        channel_id=sent_message.channel_id,
        token=interaction.token
    ).save()

    return


@modal(
    custom_id='umodal_edit',
    text_inputs=[
        TextInput(
            custom_id='message',
            style=TextInputStyle.LONG,
            max_length=2000,
            label='message',
            required=True)])
async def umodal_edit(
    interaction: Interaction,
    message_id: int,
    author_id: int,
    message: str
) -> None:

    userproxy_interaction = await UserProxyInteraction.find_one({
        'message_id': message_id
    })

    if userproxy_interaction is not None:
        webhook = Webhook.from_proxy_interaction(
            userproxy_interaction
        )

        await gather(
            webhook.edit_message(
                message_id,
                content=message
            ),
            interaction.response.ack()
        )

        return

    member = await ProxyMember.find_one({
        'userproxy.bot_id': author_id
    })

    if member is None:
        raise InteractionError('message not found')

    assert member.userproxy is not None
    assert member.userproxy.token is not None

    assert interaction.channel is not None
    try:
        og_message = await interaction.channel.fetch_message(message_id)
    except HTTPException:
        raise InteractionError(
            'message not found\ndue to discord limitations, you can\'t edit messages that are older than 15 minutes'
        ) from None

    await gather(
        og_message.edit(
            content=message,
            token=member.userproxy.token
        ),
        interaction.response.ack()
    )
