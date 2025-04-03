from plural.db import Message as DBMessage, redis

from src.commands.helpers import make_json_safe

from src.discord import (
    TextInputStyle,
    Interaction,
    TextInput,
    Message,
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

    await edit_message(
        interaction,
        message,
        content
    )


async def _edit(
    interaction: Interaction,
    message: Message
) -> None:
    from src.commands.helpers import can_edit, INLINE_REPLY

    await can_edit(interaction, message)

    db_message = await DBMessage.find_one({
        'author_id': interaction.author_id,
        'channel_id': interaction.channel_id,
        '$or': [
            {'original_id': message.id},
            {'proxy_id': message.id}
        ]
    })

    if db_message is None:
        raise RuntimeError(
            'DBMessage not found but edit check passed.\n\n'
            'this should never happen'
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
                value=(
                    message.embeds[0].description
                    if db_message.reason == '/say command' else
                    message.content.split('\n', 1)[1]
                    if INLINE_REPLY.match(message.content) else
                    message.content),
                placeholder='Enter the new content')],
            extra=[message]
        )
    )
