from src.discord import MessageReactionAddEvent
from src.db import Message


async def on_reaction_add(event: MessageReactionAddEvent) -> None:
    # ensure message author is a webhook
    if event.message_author_id is not None:
        return

    message = await Message.find_one({'proxy_id': event.message_id})

    if message is None:
        return

    if event.user_id != message.author_id:
        return

    from src.core.session import session
    from src.models import project

    resp = await session.delete(
        (
            f'https://discord.com/api/v10/channels/{event.channel_id}/messages/{event.message_id}'),
        headers={
            'Authorization': f'Bot {project.bot_token}',
            'X-Audit-Log-Reason': '/plu/ral author X reaction'
        }
    )

