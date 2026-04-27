from plural.db import Message as DBMessage, redis

from src.commands.helpers import make_json_safe

from src.discord import (
    Message,
    Interaction
)


PAGES = {
        'delete': lambda interaction, message: _delete(interaction, message)
}

async def _delete(
    interaction: Interaction,
    message: Message
) -> None:
    from src.commands.helpers import can_delete

    await can_delete(interaction, message)

    db_message = await DBMessage.find_one({
        'user': (await interaction.get_usergroup()).id,
        'channel_id': interaction.channel_id,
        '$or': [
            {'original_id': message.id},
            {'proxy_id': message.id}
        ]
    })

    if db_message is None:
        raise RuntimeError(
            'DBMessage not found but delete check passed.\n\n'
            'this should never happen'
        )

    pipeline = redis.pipeline()
    pipeline.json().set(
        f'discord:pending_delete:{message.id}', '$',
        make_json_safe(
            message.model_dump(
                mode='json',
                exclude_defaults=True)))
    pipeline.expire(f'discord:pending_delete:{message.id}', 900)
    await pipeline.execute()

    await message.delete()

    await interaction.response.ack()
