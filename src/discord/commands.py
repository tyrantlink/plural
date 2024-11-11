from .models import ApplicationCommand, Interaction, ApplicationCommandType, ApplicationCommandOption, ApplicationIntegrationType, InteractionContextType, Permission, ApplicationCommandCallbackType
from collections.abc import Callable, Awaitable
from src.discord.http import Route, request
from src.models import project
from typing import Literal
import logfire


commands: dict[str, ApplicationCommand] = {}
# ? i don't care enough to implement guild commands at the moment


async def _put_all_commands() -> None:
    await request(
        Route(
            'PUT',
            '/applications/{application_id}/commands',
            application_id=project.application_id
        ),
        json=[
            command._as_registration_dict()
            for command in commands.values()
        ]
    )


async def register_commands():
    global commands

    live_commands: dict[str, ApplicationCommand] = {
        command['name']: ApplicationCommand(**command)
        for command in await request(
            Route(
                'GET',
                '/applications/{application_id}/commands',
                application_id=project.application_id
            ),
            ignore_cache=True
        )
    }

    if commands and not live_commands:
        logfire.debug('no commands found on discord, registering all')
        await _put_all_commands()
        return

    updates: list[
        tuple[
            Literal['POST', 'PATCH', 'DELETE'],
            ApplicationCommand
        ]
    ] = []

    for command in commands.values():
        if command.name not in live_commands:
            updates.append(('POST', command))
            continue

        if live_commands[command.name] != command:
            command.id = live_commands[command.name].id
            updates.append(('PATCH', command))

    for command in live_commands.values():
        if command.name not in commands:
            updates.append(('DELETE', command))

    if len(updates) > 4:
        logfire.debug('too many updates, registering all')
        await _put_all_commands()
        return

    for method, command in updates:
        match method:
            case 'POST':
                await request(
                    Route(
                        'POST',
                        '/applications/{application_id}/commands',
                        application_id=project.application_id
                    ),
                    json=command._as_registration_dict()
                )
            case 'PATCH':
                await request(
                    Route(
                        'PATCH',
                        '/applications/{application_id}/commands/{command_id}',
                        application_id=project.application_id,
                        command_id=command.id
                    ),
                    json=command._as_registration_dict()
                )
            case 'DELETE':
                await request(
                    Route(
                        'DELETE',
                        '/applications/{application_id}/commands/{command_id}',
                        application_id=project.application_id,
                        command_id=command.id
                    )
                )

    commands = live_commands


def _base_command(
    type: ApplicationCommandType,
    name: str,
    **kwargs
) -> Callable[[ApplicationCommandCallbackType], ApplicationCommand]:
    def decorator(func: ApplicationCommandCallbackType) -> ApplicationCommand:
        command = ApplicationCommand(
            type=type,
            name=name,
            callback=func,
            **kwargs
        )

        commands.update({name: command})

        return command

    return decorator


def slash_command(
    name: str,
    description: str,
    options: list[ApplicationCommandOption] | None = None,
    default_member_permissions: Permission | None = None,
    nsfw: bool | None = None,
    integration_types: list[ApplicationIntegrationType] | None = None,
    contexts: list[InteractionContextType] | None = None
) -> Callable[[ApplicationCommandCallbackType], ApplicationCommand]:
    return _base_command(
        ApplicationCommandType.CHAT_INPUT,
        name,
        description=description,
        options=options,
        default_member_permissions=default_member_permissions,
        nsfw=nsfw,
        integration_types=integration_types,
        contexts=contexts
    )


def message_command(
    name: str,
    default_member_permissions: Permission | None = None,
    nsfw: bool | None = None,
    integration_types: list[ApplicationIntegrationType] | None = None,
    contexts: list[InteractionContextType] | None = None
) -> Callable[[ApplicationCommandCallbackType], ApplicationCommand]:
    return _base_command(
        ApplicationCommandType.MESSAGE,
        name,
        default_member_permissions=default_member_permissions,
        nsfw=nsfw,
        integration_types=integration_types,
        contexts=contexts
    )
