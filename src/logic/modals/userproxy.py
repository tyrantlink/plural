from src.discord import modal, TextInput, Interaction, TextInputStyle, MessageFlag, Webhook, Embed
from src.db import UserProxyInteraction, Reply
from asyncio import gather


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
        await interaction.response.send_message(
            content=message,
            flags=MessageFlag.NONE
        )
        return

    await Reply(
        bot_id=int(interaction.application_id),
        channel=int(interaction.channel_id or 0),
        attachment=None,
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
    message: str
) -> None:
    userproxy_interaction = await UserProxyInteraction.find_one({
        'message_id': message_id
    })

    if userproxy_interaction is None:
        await interaction.response.send_message(
            'message not found\ndue to discord limitations, you can\'t edit messages that are older than 15 minutes',
        )
        return None

    webhook = Webhook.from_proxy_interaction(
        userproxy_interaction,
        interaction.application_id
    )

    await gather(
        webhook.edit_message(
            message_id,
            content=message
        ),
        interaction.response.ack()
    )
