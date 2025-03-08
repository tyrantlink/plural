from __future__ import annotations

from typing import Any

from beanie import PydanticObjectId

from plural.errors import InteractionError, Forbidden
from plural.missing import is_not_missing
from plural.db import ProxyMember, Group
from plural.otel import span, cx

from src.core.errors import on_interaction_error
from src.core.models import env

from src.discord.components import components
from src.discord.commands import commands
from src.discord import (
    ApplicationCommandInteractionData,
    MessageComponentInteractionData,
    ApplicationCommandOptionType,
    ModalSubmitInteractionData,
    ApplicationCommandScope,
    ApplicationCommandType,
    CustomIdExtraType,
    InteractionType,
    ComponentType,
    Interaction,
    ActionRow,
    Snowflake,
    Message,
    Channel,
    User,
)

from .converter import member_converter, group_converter, proxy_tag_converter
from .autocomplete import on_autocomplete


# ? i'm so good at names
type CustomIdExtraTypeType = None | str | int | bool | User | Channel | ProxyMember | Group | Message


async def on_interaction(interaction: Interaction, latency: int) -> None:
    if interaction.type == InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE:
        try:
            return await on_autocomplete(interaction)
        except Exception as e:  # noqa: BLE001
            await on_interaction_error(interaction, e)

    with span(
        'uninitialized interaction',
        attributes={
            'interaction.latency': latency
        }
    ):
        try:
            match interaction.type:
                case InteractionType.APPLICATION_COMMAND:
                    await _on_application_command(interaction)
                case InteractionType.MESSAGE_COMPONENT:
                    await _on_message_component(interaction)
                case InteractionType.MODAL_SUBMIT:
                    await _on_modal_submit(interaction)
        except Exception as e:  # noqa: BLE001
            await on_interaction_error(interaction, e)


async def _on_application_command(interaction: Interaction) -> None:
    assert isinstance(interaction.data, ApplicationCommandInteractionData)
    ###! migration
    from src.components import PAGES
    if await PAGES['migrate'](interaction):
        cx().update_name('MIGRATION OVERRIDE')
        return
    ###! migration

    scope = (
        ApplicationCommandScope.PRIMARY
        if interaction.application_id == env.application_id else
        ApplicationCommandScope.USERPROXY
    )

    command = commands[scope].get(interaction.data.name)

    if (
        command is None and
        scope is ApplicationCommandScope.USERPROXY and (
            member := await ProxyMember.find_one(
                ProxyMember.userproxy.bot_id == interaction.application_id)
        ) is not None and
        member.userproxy is not None
    ):
        match interaction.data.name:
            case member.userproxy.command:
                command = commands[
                    ApplicationCommandScope.USERPROXY
                ].get('proxy')
            case name if name.startswith('Reply '):
                command = commands[
                    ApplicationCommandScope.USERPROXY
                ].get('Reply')

    if command is None:
        raise InteractionError(
            f'command `{interaction.data.name}` not found'
        )

    callback = command.callback
    command_options = command.options or []
    options = interaction.data.options or []

    qualified_name = command.name

    while callback is None:
        subcommand = options[0]
        for option in command_options:

            if subcommand.name == option.name:
                match option.type:
                    case ApplicationCommandOptionType.SUB_COMMAND_GROUP:
                        qualified_name += f' {option.name}'
                        command_options = option.options or []
                        options = subcommand.options or []
                    case ApplicationCommandOptionType.SUB_COMMAND:
                        qualified_name += f' {option.name}'
                        options = subcommand.options or []
                        callback = option.callback
                    case _:
                        continue
                break
        else:
            raise ValueError(
                f'no callback found for {interaction.data.name}')

    cx().update_name(
        f'{'/' if command.type == ApplicationCommandType.CHAT_INPUT else ''}{qualified_name}'
    )

    kwargs: dict[str, Any] = await parse_command_options(
        interaction, options
    )

    match command.type:
        case ApplicationCommandType.MESSAGE:
            assert interaction.data.resolved is not None
            assert interaction.data.resolved.messages is not None
            assert interaction.data.target_id is not None
            kwargs['message'] = interaction.data.resolved.messages.get(
                Snowflake(interaction.data.target_id))
        case ApplicationCommandType.USER:
            ...

    cx().set_attributes({
        'user.name': interaction.author_name,
        'user.id': str(interaction.author_id),
        'guild.id': str(interaction.guild_id or 'dm'),
        'options': [  # ? value included in dev, only name in prod
            (f'{option}: {value}' if env.dev else option)
            for option, value in kwargs.items()
        ]
    })

    await callback(interaction, **kwargs)


async def _on_message_component(interaction: Interaction) -> None:
    assert isinstance(interaction.data, MessageComponentInteractionData)

    component_name, args = await parse_custom_id(
        interaction,
        interaction.data.custom_id
    )

    cx().update_name(
        f'{interaction.data.component_type.name} {component_name}'
    )

    triggered_component = components.get(component_name)

    if triggered_component is None or not is_not_missing(triggered_component.callback):
        raise ValueError(f'no component found for {component_name}')

    kwargs = {}

    match interaction.data.component_type:
        case ComponentType.STRING_SELECT:
            args.insert(0, interaction.data.values)

    cx().set_attributes({
        'user.name': interaction.author_name,
        'user.id': str(interaction.author_id),
        'guild.id': str(interaction.guild_id) or 'dm',
        'args': [str(arg) for arg in args]
    })

    await triggered_component.callback(interaction, *args, **kwargs)


async def _on_modal_submit(interaction: Interaction) -> None:
    assert isinstance(interaction.data, ModalSubmitInteractionData)
    try:
        component_name, args = await parse_custom_id(
            interaction,
            interaction.data.custom_id)
    except BaseException as e:  # noqa: BLE001
        component_name = interaction.data.custom_id.split('.')[0]
        cx().update_name(f'MODAL_SUBMIT {component_name}')
        await on_interaction_error(interaction, e)
        return

    cx().update_name(
        f'MODAL_SUBMIT {component_name}'
    )

    triggered_component = components.get(component_name)

    if triggered_component is None or not is_not_missing(triggered_component.callback):
        raise ValueError(f'no component found for {component_name}')

    kwargs = {
        component.custom_id: component.value
        for component in (
            interaction.data.components or
            [ActionRow(components=[])]
        )[0].components
    }

    cx().set_attributes({
        'user.name': interaction.author_name,
        'user.id': str(interaction.author_id),
        'guild.id': str(interaction.guild_id) or 'dm',
        'args': [str(arg) for arg in args]
    })

    await triggered_component.callback(interaction, *args, **kwargs)


async def parse_command_options(
    interaction: Interaction,
    options: list[ApplicationCommandInteractionData.Option]
) -> dict[str, Any]:
    assert isinstance(interaction.data, ApplicationCommandInteractionData)
    kwargs: dict[str, Any] = {}

    for option in options:
        if option.name == 'global':
            option.name = 'global_'

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
                converter_kwargs = {}
                match option.name:
                    case 'member' | 'userproxy':
                        converter = member_converter
                        converter_kwargs['userproxy'] = option.name == 'userproxy'
                    case 'group':
                        converter = group_converter
                    case 'proxy_tag':
                        converter = proxy_tag_converter
                    case _:
                        kwargs[option.name] = option.value
                        continue
                try:
                    kwargs[option.name] = await converter(
                        interaction,
                        option.value,
                        **converter_kwargs)
                except InteractionError as e:
                    await on_interaction_error(interaction, e)
            case _:
                kwargs[option.name] = option.value

    return kwargs


async def parse_custom_id(
    interaction: Interaction,
    custom_id: str
) -> tuple[str, list[CustomIdExtraTypeType]]:
    base, *extras = custom_id.split('.')
    bot_token = env.bot_token
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
            case CustomIdExtraType.MEMBER:
                args.append(await ProxyMember.get(PydanticObjectId(arg[1:])))
            case CustomIdExtraType.GROUP:
                args.append(await Group.get(PydanticObjectId(arg[1:])))
            case CustomIdExtraType.MESSAGE:
                if (
                    interaction.application_id != env.application_id and
                    bot_token == env.bot_token
                ):
                    member = await ProxyMember.find_one({
                        'userproxy.bot_id': interaction.application_id
                    })

                    if member is None or member.userproxy is None:
                        raise InteractionError('Invalid application id')

                    bot_token = member.userproxy.token

                    try:
                        args.append(await Message.fetch(
                            *(Snowflake(i) for i in arg[1:].split(':')),
                            bot_token=bot_token))
                    except Forbidden as e:
                        raise InteractionError(
                            'Unable to fetch message'
                        ) from e
            case _:
                raise ValueError(f'invalid extra type `{arg}`')

    return base, args
