from src.discord import modal, TextInput, Interaction, TextInputStyle, MessageFlag, Webhook, Embed
from src.db import UserProxyInteraction, Reply, ProxyMember
from src.errors import InteractionError, HTTPException
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
    message: str
) -> None:
    if not queue_for_reply:
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

    await Reply(
        bot_id=int(interaction.application_id),
        channel=int(interaction.channel_id or 0),
        attachments=[],
        content=message
    ).save()

    await interaction.response.send_message(
        embeds=[
            Embed.success(
                title='message queued for reply',
                message='use the reply command within the next 5 minutes to send your message'
            )
        ],
    )
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
