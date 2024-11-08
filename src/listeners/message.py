from src.discord import MessageCreateEvent, MessageUpdateEvent


async def on_message_create(event: MessageCreateEvent) -> None:
    print(event)


async def on_message_update(event: MessageUpdateEvent) -> None:
    print(event)
