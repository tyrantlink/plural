from src.discord import MessageCreateEvent, MessageUpdateEvent, MessageReactionAddEvent, Channel, MessageType, ChannelType, Interaction, ApplicationCommandInteractionData, MessageComponentInteractionData, ModalSubmitInteractionData, ApplicationCommandOptionType, Snowflake, ApplicationCommandType, ActionRow, TextInput, ModalExtraType, User
from src.db import Message as DBMessage, Member as ProxyMember, Group
from src.discord.commands import commands, ApplicationCommandScope
from src.discord.models.modal import ModalExtraTypeType
from src.discord.listeners import listen, ListenerType
from .proxy import process_proxy, get_proxy_webhook  # , handle_ping_reply
from src.discord.components import components
from beanie import PydanticObjectId
from src.models import project
from asyncio import gather
from typing import Any


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

    scope = (
        ApplicationCommandScope.PRIMARY
        if interaction.application_id == project.application_id else
        ApplicationCommandScope.USERPROXY
    )
    command = commands[scope].get(interaction.data.name)

    if (
        command is None and
        scope == ApplicationCommandScope.USERPROXY and
        (
            member := await ProxyMember.find_one(
            {'userproxy.bot_id': interaction.application_id})
        ) is not None and
        member.userproxy is not None and
        member.userproxy.command == interaction.data.name
    ):
        command = commands[ApplicationCommandScope.USERPROXY].get('proxy')

    if command is None:
        raise ValueError(
            f'no command found for {interaction.data.name}')

    callback = command.callback
    command_options = command.options or []
    options = interaction.data.options or []

    while callback is None:
        subcommand = options[0]
        for option in command_options:

            if subcommand.name == option.name:

                if option.type == ApplicationCommandOptionType.SUB_COMMAND_GROUP:
                    command_options = option.options or []
                    options = subcommand.options or []
                    break

                if option.type == ApplicationCommandOptionType.SUB_COMMAND:
                    options = subcommand.options or []
                    callback = option.callback
                    break
        else:
            raise ValueError(
                f'no callback found for {interaction.data.name}')

    kwargs: dict[str, Any] = {}

    match command.type:
        case ApplicationCommandType.MESSAGE:
            assert interaction.data.resolved is not None
            assert interaction.data.resolved.messages is not None
            assert interaction.data.target_id is not None
            kwargs['message'] = interaction.data.resolved.messages.get(
                Snowflake(interaction.data.target_id)
            )
        case ApplicationCommandType.USER:
            ...

    for option in options:
        match option.type:
            case ApplicationCommandOptionType.ATTACHMENT:
                assert interaction.data.resolved is not None
                assert interaction.data.resolved.attachments is not None
                assert isinstance(option.value, str)

                kwargs[option.name] = interaction.data.resolved.attachments[
                    Snowflake(option.value)
                ]
            case _:
                kwargs[option.name] = option.value

    await callback(interaction, **kwargs)


async def parse_custom_id(
    custom_id: str
) -> tuple[str, list[ModalExtraTypeType]]:
    base, *extras = custom_id.split('.')
    args = []
    for arg in extras:
        match ModalExtraType(arg[0]):
            case ModalExtraType.NONE:
                args.append(None)
            case ModalExtraType.STRING:
                args.append(arg[1:])
            case ModalExtraType.INTEGER:
                args.append(int(arg[1:]))
            case ModalExtraType.BOOLEAN:
                args.append(bool(int(arg[1:])))
            case ModalExtraType.USER:
                args.append(await User.fetch(Snowflake(arg[1:])))
            case ModalExtraType.CHANNEL:
                args.append(await Channel.fetch(Snowflake(arg[1:])))
            case ModalExtraType.MEMBER:
                args.append(await ProxyMember.get(PydanticObjectId(arg[1:])))
            case ModalExtraType.GROUP:
                args.append(await Group.get(PydanticObjectId(arg[1:])))
            case _:
                raise ValueError(f'invalid extra type `{arg}`')

    return base, args


async def _on_message_component(interaction: Interaction) -> None:
    assert isinstance(interaction.data, MessageComponentInteractionData)
    print('message component')
    print(interaction.data._raw)

    component_name, args = await parse_custom_id(
        interaction.data.custom_id
    )


async def _on_modal_submit(interaction: Interaction) -> None:
    assert isinstance(interaction.data, ModalSubmitInteractionData)

    modal_name, args = await parse_custom_id(
        interaction.data.custom_id
    )

    modal = components.get(modal_name)

    if modal is None or modal.callback is None:
        raise ValueError(f'no modal found for {modal_name}')

    kwargs = {
        component.custom_id: component.value
        for component in [
            component
            for component in (
                interaction.data.components or
                [ActionRow(components=[])]
            )[0].components
            if isinstance(component, TextInput)
        ]
    }

    await modal.callback(interaction, *args, **kwargs)


@listen(ListenerType.INTERACTION)
async def on_interaction(interaction: Interaction) -> None:
    #! note for when doing message components
    #! order of interaction.data typehint might be fucky
    match interaction.data:
        case ApplicationCommandInteractionData():
            await _on_application_command(interaction)
        case MessageComponentInteractionData():
            await _on_message_component(interaction)
        case ModalSubmitInteractionData():
            await _on_modal_submit(interaction)
