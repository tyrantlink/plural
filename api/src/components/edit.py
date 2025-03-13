from plural.db import Interaction as DBInteraction, redis
from plural.errors import InteractionError

from src.commands.helpers import make_json_safe

from src.discord import (
    TextInputStyle,
    Interaction,
    TextInput,
    Message,
    Webhook,
    modal
)


PAGES = {
    'edit': lambda interaction, message: _edit(interaction, message)
}


@modal(
    custom_id='modal_edit',
    title='Edit Message',
    text_inputs=[])
async def modal_edit(
    interaction: Interaction,
    message: Message,
    content: str
) -> None:
    from src.commands.helpers import edit_message

    if not message.interaction_metadata:
        await edit_message(interaction, message, content)
        return

    db_interaction = await DBInteraction.find_one({
        'author_id': interaction.author_id,
        'bot_id': message.author.id,
        'channel_id': interaction.channel_id,
        'message_id': message.id
    })

    if db_interaction is None:
        raise InteractionError(
            'No message found\n\n'
            'Messages older than 15 minutes cannot be edited'
        )

    await edit_message(
        interaction,
        message,
        content,
        Webhook.from_proxy_interaction(db_interaction)
    )


async def _edit(
    interaction: Interaction,
    message: Message
) -> None:
    from src.commands.helpers import can_edit

    if not await can_edit(interaction, message):
        raise InteractionError(
            'You cannot edit this message, '
            'it is either not a /plu/ral message, older than 7 days, '
            'or you are not the author of the message'
        )

    pipeline = redis.pipeline()
    pipeline.json().set(
        f'discord:pending_edit:{message.id}', '$',
        make_json_safe(
            message.model_dump(
                mode='json',
                exclude_defaults=True)))
    pipeline.expire(f'discord:pending_edit:{message.id}', 900)
    await pipeline.execute()

    await interaction.response.send_modal(
        modal_edit.with_overrides(
            text_inputs=[TextInput(
                custom_id='content',
                style=TextInputStyle.PARAGRAPH,
                label='Message',
                min_length=1,
                max_length=2000,
                required=True,
                value=message.content,
                placeholder='Enter the new content')],
            extra=[message]
        )
    )
