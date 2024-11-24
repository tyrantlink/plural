from src.discord import MessageCreateEvent, MessageUpdateEvent, MessageReactionAddEvent, Channel, MessageType, Interaction, ApplicationCommandInteractionData, MessageComponentInteractionData, ModalSubmitInteractionData, ApplicationCommandOptionType, Snowflake, ApplicationCommandType, ActionRow, TextInput, CustomIdExtraType, User, Message, InteractionType, ApplicationCommandInteractionDataOption, ComponentType, ApplicationAuthorizedEvent, WebhookEvent, EventType, ApplicationIntegrationType
from src.discord.commands import commands, ApplicationCommandScope
from src.db import Message as DBMessage, ProxyMember, Group
from src.discord.models.modal import CustomIdExtraTypeType
from .converters import member_converter, group_converter
from src.discord.listeners import listen, ListenerType
from .proxy import process_proxy, get_proxy_webhook
from src.discord.components import components
from .autocomplete import on_autocomplete
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

    proxied, app_emojis, token, db_message = await process_proxy(message)

    if app_emojis:
        gather(*[emoji.delete(token) for emoji in app_emojis])

    if proxied:
        return


@listen(ListenerType.MESSAGE_UPDATE)
async def on_message_edit(message: MessageUpdateEvent):
    if (
        not message.author or
        message.author.bot or
        message.channel is None or
        message.type == MessageType.THREAD_CREATED
    ):
        return

    if await message.channel.fetch_messages(limit=1) != [message]:
        return None

    await on_message(message)


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
            db_message = await DBMessage.find_one(
                {'proxy_id': reaction.message_id}
            )

            if db_message is None:
                return

            if reaction.user_id != db_message.author_id:
                return

            channel, message = await gather(
                Channel.fetch(reaction.channel_id),
                Message.fetch(reaction.channel_id, reaction.message_id)
            )

            if channel is None or message is None:
                return

            if message.webhook_id is None:
                assert message.author is not None
                userproxy = await ProxyMember.find_one(
                    {'userproxy.bot_id': message.author.id})

                if userproxy is None:
                    return

                assert userproxy.userproxy is not None

                if userproxy.userproxy.token is None:
                    await channel.send(
                        'userproxy must have a token stored to delete messages',
                        delete_after=10,
                        reference=message
                    )

                await message.delete(
                    'userproxy message deleted',
                    token=userproxy.userproxy.token)

                return

            webhook = await get_proxy_webhook(
                channel
            )

            await webhook.delete_message(
                reaction.message_id,
                thread_id=(
                    channel.id
                    if channel.is_thread else
                    None
                )
            )


async def parse_command_options(
    interaction: Interaction,
    options: list[ApplicationCommandInteractionDataOption]
) -> dict[str, Any]:
    assert isinstance(interaction.data, ApplicationCommandInteractionData)
    kwargs: dict[str, Any] = {}

    for option in options:
        match option.type:
            case ApplicationCommandOptionType.ATTACHMENT:
                assert interaction.data.resolved is not None
                assert interaction.data.resolved.attachments is not None
                assert isinstance(option.value, str)

                kwargs[option.name] = interaction.data.resolved.attachments[
                    Snowflake(option.value)]
            case ApplicationCommandOptionType.USER:
                assert interaction.data.resolved is not None
                assert interaction.data.resolved.users is not None
                assert isinstance(option.value, str)

                kwargs[option.name] = interaction.data.resolved.users[
                    Snowflake(option.value)]
            case ApplicationCommandOptionType.CHANNEL:
                assert interaction.data.resolved is not None
                assert interaction.data.resolved.channels is not None
                assert isinstance(option.value, str)

                kwargs[option.name] = interaction.data.resolved.channels[
                    Snowflake(option.value)]
            case ApplicationCommandOptionType.STRING:
                assert isinstance(option.value, str)
                match option.name:
                    case 'member' | 'userproxy':
                        converter = member_converter
                    case 'group':
                        converter = group_converter
                    case _:
                        kwargs[option.name] = option.value
                        continue

                kwargs[option.name] = await converter(
                    interaction,
                    {
                        o.name: o
                        for o in options
                    },
                    option.value
                )
            case _:
                kwargs[option.name] = option.value

    return kwargs


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

                match option.type:
                    case ApplicationCommandOptionType.SUB_COMMAND_GROUP:
                        command_options = option.options or []
                        options = subcommand.options or []
                    case ApplicationCommandOptionType.SUB_COMMAND:
                        options = subcommand.options or []
                        callback = option.callback
                    case _:
                        continue
                break
        else:
            raise ValueError(
                f'no callback found for {interaction.data.name}')

    kwargs: dict[str, Any] = await parse_command_options(
        interaction, options
    )

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

    await callback(interaction, **kwargs)


async def parse_custom_id(
    custom_id: str
) -> tuple[str, list[CustomIdExtraTypeType]]:
    base, *extras = custom_id.split('.')
    args = []
    for arg in extras:
        match CustomIdExtraType(arg[0]):
            case CustomIdExtraType.NONE:
                args.append(None)
            case CustomIdExtraType.STRING:
                args.append(arg[1:])
            case CustomIdExtraType.INTEGER:
                args.append(int(arg[1:]))
            case CustomIdExtraType.BOOLEAN:
                args.append(bool(int(arg[1:])))
            case CustomIdExtraType.USER:
                args.append(await User.fetch(Snowflake(arg[1:])))
            case CustomIdExtraType.CHANNEL:
                args.append(await Channel.fetch(Snowflake(arg[1:])))
            case CustomIdExtraType.MEMBER:
                args.append(await ProxyMember.get(PydanticObjectId(arg[1:])))
            case CustomIdExtraType.GROUP:
                args.append(await Group.get(PydanticObjectId(arg[1:])))
            case CustomIdExtraType.MESSAGE:
                args.append(
                    await Message.fetch(
                        *(Snowflake(i) for i in arg[1:].split(':')),
                        populate=True
                    )
                )
            case _:
                raise ValueError(f'invalid extra type `{arg}`')

    return base, args


async def _on_message_component(interaction: Interaction) -> None:
    assert isinstance(interaction.data, MessageComponentInteractionData)

    component_name, args = await parse_custom_id(
        interaction.data.custom_id
    )

    triggered_component = components.get(component_name)

    if triggered_component is None or triggered_component.callback is None:
        raise ValueError(f'no component found for {component_name}')

    match interaction.data.component_type:
        case ComponentType.BUTTON:
            await triggered_component.callback(interaction, *args)
        case _:
            raise NotImplementedError(
                f'unsupported component type {interaction.data.component_type}')


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
    match interaction.type:
        case InteractionType.APPLICATION_COMMAND:
            await _on_application_command(interaction)
        case InteractionType.MESSAGE_COMPONENT:
            await _on_message_component(interaction)
        case InteractionType.MODAL_SUBMIT:
            await _on_modal_submit(interaction)
        case InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE:
            await on_autocomplete(interaction)


async def _on_application_authorization(
    application_id: Snowflake,
    event: ApplicationAuthorizedEvent
) -> None:
    if (
        event.integration_type != ApplicationIntegrationType.GUILD_INSTALL or
        not event.guild
    ):
        return

    member = await ProxyMember.find_one(
        {'userproxy.bot_id': application_id}
    )

    if member is None or member.userproxy is None:
        return

    member.userproxy.guilds.append(event.guild.id)

    member.userproxy.guilds = list(set(member.userproxy.guilds))

    await member.save()


@listen(ListenerType.WEBHOOK_EVENT)
async def on_webhook_event(event: WebhookEvent) -> None:
    if not event.event:
        return

    match event.event.type:
        case EventType.APPLICATION_AUTHORIZED:
            assert isinstance(event.event.data, ApplicationAuthorizedEvent)
            await _on_application_authorization(
                event.application_id,
                event.event.data)
        # ? will implement more when needed
