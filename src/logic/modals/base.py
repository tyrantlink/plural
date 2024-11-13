from src.discord import modal, TextInput, Interaction, TextInputStyle, MessageFlag, Webhook, Embed, Message
from src.db import UserProxyInteraction, Reply, Webhook as DBWebhook
from src.logic.proxy import get_proxy_webhook
from src.errors import InteractionError
from asyncio import gather

__all__ = ('modal_plural_edit',)


@modal(
    title='edit message',
    custom_id='modal_plural_edit',
    text_inputs=[
        TextInput(
            custom_id='new_message',
            style=TextInputStyle.LONG,
            max_length=2000,
            label='message',
            required=True)])
async def modal_plural_edit(
    interaction: Interaction,
    message: Message,
    new_message: str
) -> None:
    assert message.channel is not None

    if new_message == message.content:
        raise InteractionError('no changes were made')

    webhook = await get_proxy_webhook(message.channel)

    await gather(
        interaction.response.ack(),
        webhook.edit_message(
            message.id,
            content=new_message,
            thread_id=(
                message.channel.id
                if message.channel.is_thread else
                None
            )
        )
    )
