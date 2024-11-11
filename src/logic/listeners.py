from src.discord import MessageCreateEvent, MessageUpdateEvent, MessageReactionAddEvent, Channel, MessageType, ChannelType, Interaction, ApplicationCommandInteractionData, MessageComponentInteractionData, ModalSubmitInteractionData
from src.discord.listeners import listen, ListenerType
from .proxy import process_proxy, get_proxy_webhook  # , handle_ping_reply
from src.discord.commands import commands
from src.db import Message as DBMessage
from src.models import project
from asyncio import gather


@listen(ListenerType.MESSAGE_CREATE)
async def on_message(message: MessageCreateEvent):
    if (
        not message.author or
        message.author.bot or
        message.channel is None or
        message.type == MessageType.THREAD_CREATED
    ):
        return

    proxied, app_emojis = await process_proxy(message)

    if app_emojis:
        gather(*[emoji.delete() for emoji in app_emojis])

    if proxied:
        return


@listen(ListenerType.MESSAGE_UPDATE)
async def on_message_edit(message: MessageUpdateEvent):
    if message.channel is None:
        return

    # if await message.channel.history(limit=1).flatten() != [message]:
    #     return None

    # await on_message(message)


@listen(ListenerType.MESSAGE_REACTION_ADD)
async def on_reaction_add(reaction: MessageReactionAddEvent):
    if (
        reaction.user_id == project.application_id or
        reaction.guild_id is None or
        reaction.member is None or
        reaction.member.user is None or
        reaction.member.user.bot or
        reaction.emoji.name not in {'❌'}
    ):
        return

    match reaction.emoji.name:  # ? i might add more later
        case '❌':
            message = await DBMessage.find_one(
                {'proxy_id': reaction.message_id}
            )

            if message is None:
                return

            if reaction.user_id != message.author_id:
                return

            channel = await Channel.fetch(reaction.channel_id)

            if channel is None:
                return

            webhook = await get_proxy_webhook(
                channel
            )

            await webhook.delete_message(
                reaction.message_id,
                thread_id=(
                    channel.id
                    if channel.type in {ChannelType.PUBLIC_THREAD, ChannelType.PRIVATE_THREAD} else
                    None
                )
            )


async def _on_application_command(interaction: Interaction) -> None:
    assert isinstance(interaction.data, ApplicationCommandInteractionData)
    command = commands.get(interaction.data.name)
    if command is None or command.callback is None:
        return

    args = [  # ? figure out resolved args
        option.value
        for option in interaction.data.options or []
    ]

    await command.callback(interaction, *args)


async def _on_message_component(interaction: Interaction) -> None:
    assert isinstance(interaction.data, MessageComponentInteractionData)


async def _on_modal_submit(interaction: Interaction) -> None:
    assert isinstance(interaction.data, ModalSubmitInteractionData)


@listen(ListenerType.INTERACTION)
async def on_interaction(interaction: Interaction) -> None:
    match interaction.data:
        case ApplicationCommandInteractionData():
            await _on_application_command(interaction)
        case MessageComponentInteractionData():
            await _on_message_component(interaction)
        case ModalSubmitInteractionData():
            await _on_modal_submit(interaction)
