from asyncio import gather

from plural.db.enums import ReplyType
from plural.db import (
    Message as DBMessage,
    ProxyMember,
    Reply
)

from src.discord import (
    InteractionContextType,
    AllowedMentions,
    TextInputStyle,
    Interaction,
    MessageFlag,
    TextInput,
    Message,
    Embed,
    modal
)

from src.commands.helpers import format_reply


PAGES = {
    'proxy': lambda interaction, queue_for_reply, message: _proxy(interaction, queue_for_reply, message)
}


@modal(
    custom_id='modal_proxy',
    title='Send Message',
    text_inputs=[])
async def modal_proxy(
    interaction: Interaction,
    queue_for_reply: bool,
    reply_id: int | None = None,
    message: str = ''
) -> None:
    if queue_for_reply:
        await gather(
            Reply(
                type=ReplyType.QUEUE,
                bot_id=interaction.application_id,
                channel=interaction.channel_id or 0,
                attachments=[],
                content=message,
                message_id=None,
                author=None,
                webhook_id=None
            ).save(),
            interaction.response.send_message(
                embeds=[Embed.success(
                    title='Message Queued for Reply',
                    message='Use the Reply message command within the next 5 minutes to send the message'
                )]
            ))
        return

    reply = await Reply.find_one({
        'bot_id': interaction.application_id,
        'channel': interaction.channel_id or 0,
        'type': ReplyType.REPLY,
        'message_id': reply_id
    })

    usergroup = await interaction.get_usergroup()

    if reply is None:
        sent_message = await interaction.response.send_message(
            content=message,
            flags=MessageFlag.NONE,
            with_response=True
        )

        await DBMessage(
            original_id=None,
            proxy_id=sent_message.id,
            author_id=interaction.author_id,
            user=usergroup.id,
            channel_id=interaction.channel_id,
            member_id=(await ProxyMember.find_one({
                'userproxy.bot_id': interaction.application_id})).id,
            reason=f'Userproxy {'Reply' if reply_id else '/proxy'} command',
            reference_id=reply_id,
            bot_id=interaction.application_id,
            interaction_token=interaction.token
        ).save()
        return

    if reply.author is None:
        raise ValueError('Reply author is None')

    usergroup = await interaction.get_usergroup()
    member = await ProxyMember.find_one(
        {'userproxy.bot_id': interaction.application_id}
    )

    reply_format = (
        usergroup.userproxy_config.reply_format
        if interaction.context == InteractionContextType.GUILD else
        usergroup.userproxy_config.dm_reply_format
    )

    reply_insert = format_reply(
        message,
        reply,
        reply_format,
        interaction.guild_id or None,
        member.color
    )[0]

    embeds = []

    match reply_insert:
        case str():
            message = reply_insert
        case Embed():
            embeds.append(reply_insert)

    mentions = AllowedMentions.parse_content(
        reply.content,
        False
    )

    mentions.users.update(
        {reply.author.id}
        if usergroup.userproxy_config.ping_replies else
        set()
    )

    sent_message = await interaction.send(
        message,
        embeds=embeds,
        allowed_mentions=mentions,
        with_response=True,
        flags=MessageFlag.NONE
    )

    await DBMessage(
        original_id=None,
        proxy_id=sent_message.id,
        author_id=interaction.author_id,
        user=usergroup.id,
        channel_id=interaction.channel_id,
        member_id=member.id,
        reason='Userproxy Reply command',
        reference_id=reply_id,
        bot_id=interaction.application_id,
        interaction_token=interaction.token,
    ).save()


async def _proxy(
    interaction: Interaction,
    queue_for_reply: bool,
    message: Message | None
) -> None:
    title = (
        f'Reply to {message.author.username}'
        if message else
        'Send a message'
    )

    if len(title) > 45:
        title = 'Reply to a message'

    await interaction.response.send_modal(
        modal_proxy.with_overrides(
            title=title,
            text_inputs=[TextInput(
                custom_id='message',
                style=TextInputStyle.PARAGRAPH,
                label='Message',
                min_length=1,
                max_length=2000,
                required=True,
                placeholder='This should only be used if you need to send newlines or very long messages')],
            extra=[
                queue_for_reply,
                message.id if message else None
            ]
        )
    )
