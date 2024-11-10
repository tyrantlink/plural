from src.discord import MessageCreateEvent, MessageUpdateEvent
from src.discord.listeners import listen, ListenerType
# from .webhook_proxy import process_proxy  # , handle_ping_reply
from asyncio import gather


@listen(ListenerType.MESSAGE_CREATE)
async def on_message(message: MessageCreateEvent):
    if not message.author or message.author.bot:
        return

    if message.guild:
        print(message.guild.name)
    # proxied, app_emojis = await process_proxy(message)

    # if app_emojis:
    #     await gather(
    #         *[
    #             emoji.delete()
    #             for emoji in
    #             app_emojis
    #         ]
    #     )

    # if proxied:
    #     return

    # if await handle_ping_reply(message):
    #     return

    # if (  # ? stealing the pk easter egg because it's funny
    #     message.author is not None and
    #     not message.author.bot and
    #     message.content.startswith('pk;') and
    #     message.content.lstrip('pk;').strip() == 'fire'  # and
    #     # message.channel.can_send()
    # ):
    #     await message.channel.send('*A giant lightning bolt promptly erupts into a pillar of fire as it hits your opponent.*')


@listen(ListenerType.MESSAGE_UPDATE)
async def on_message_edit(message: MessageUpdateEvent):
    ...
    # proxied, app_emojis = await process_proxy(message)

    # for emoji in app_emojis or set():
    #     await emoji.delete()
