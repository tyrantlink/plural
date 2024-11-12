from .models import ApplicationCommand, ApplicationCommandType, ApplicationCommandOption, ApplicationIntegrationType, InteractionContextType, Permission, InteractionCallback
from src.db import Member as ProxyMember, HTTPCache
from src.discord.http import Route, request
from collections.abc import Callable
from src.models import project
from typing import Literal
from copy import deepcopy
from enum import Enum
import logfire


class ApplicationCommandScope(Enum):
    PRIMARY = 0
    USERPROXY = 1


commands: dict[ApplicationCommandScope, dict[str, ApplicationCommand]] = {
    ApplicationCommandScope.PRIMARY: {},
    ApplicationCommandScope.USERPROXY: {}
}
# ? i don't care enough to implement guild commands


async def _put_all_commands(
    token: str
) -> None:
    await request(
        Route(
            'PUT',
            '/applications/{application_id}/commands',
            application_id=project.application_id
        ),
        json=[
            command._as_registration_dict()
            for command in commands[ApplicationCommandScope.PRIMARY].values()
        ]
    )


async def _sync_commands(
    application_id: int = project.application_id,
    token: str | None = None
) -> None:
    global commands
    scope = (
        ApplicationCommandScope.PRIMARY
        if application_id == project.application_id else
        ApplicationCommandScope.USERPROXY
    )

    member = None
    token = token or (
        member.userproxy.token
        if (
            scope == ApplicationCommandScope.USERPROXY and
            (
                member := await ProxyMember.find_one({'userproxy.bot_id': application_id})
            ) and
            member.userproxy is not None and
            member.userproxy.token is not None

        ) else
        project.bot_token
    )

    live_commands: dict[str, ApplicationCommand] = {
        command['name']: ApplicationCommand(**command)
        for command in await request(
            Route(
                'GET',
                '/applications/{application_id}/commands',
                application_id=application_id
            ),
            token=token
        )
    }

    working_commands = commands[scope]

    # ? inject custom userproxy 'proxy' command name
    if scope == ApplicationCommandScope.USERPROXY and 'proxy' in working_commands:
        working_commands = deepcopy(working_commands)

        if member and member.userproxy and member.userproxy.command:
            command = working_commands.pop('proxy')
            command.name = member.userproxy.command
            working_commands[command.name] = command

        working_commands.update(commands[ApplicationCommandScope.PRIMARY])

    if working_commands != live_commands:
        await HTTPCache.invalidate(f'/applications/{application_id}/commands')

    if working_commands and not live_commands:
        logfire.debug('no commands found on discord, registering all')
        await _put_all_commands(token)
        return

    updates: list[
        tuple[
            Literal['POST', 'PATCH', 'DELETE'],
            ApplicationCommand
        ]
    ] = []

    for command in working_commands.values():
        if command.name not in live_commands:
            updates.append(('POST', command))
            continue

        if live_commands[command.name] != command:
            command.id = live_commands[command.name].id
            updates.append(('PATCH', command))

    for command in live_commands.values():
        if command.name not in working_commands:
            updates.append(('DELETE', command))

    if len(updates) > 4:
        logfire.debug('too many updates, registering all')
        await _put_all_commands(token)
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
                    json=command._as_registration_dict(),
                    token=token
                )
            case 'PATCH':
                await request(
                    Route(
                        'PATCH',
                        '/applications/{application_id}/commands/{command_id}',
                        application_id=project.application_id,
                        command_id=command.id
                    ),
                    json=command._as_registration_dict(),
                    token=token
                )
            case 'DELETE':
                await request(
                    Route(
                        'DELETE',
                        '/applications/{application_id}/commands/{command_id}',
                        application_id=project.application_id,
                        command_id=command.id
                    ),
                    token=token
                )


async def sync_commands(
    application_id: int = project.application_id,
    token: str | None = None
) -> None:
    if project.logfire_token:
        with logfire.span('sync_commands with {application_id}', application_id=application_id):
            await _sync_commands(application_id, token)
        return

    await _sync_commands(application_id, token)


def _base_command(
    type: ApplicationCommandType,
    name: str,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY,
    **kwargs
) -> Callable[[InteractionCallback], ApplicationCommand]:
    def decorator(func: InteractionCallback) -> ApplicationCommand:
        command = ApplicationCommand(
            type=type,
            name=name,
            callback=func,
            **kwargs
        )

        commands[scope].update({name: command})

        return command

    return decorator


def slash_command(
    name: str,
    description: str,
    options: list[ApplicationCommandOption] | None = None,
    default_member_permissions: Permission | None = None,
    nsfw: bool = False,
    integration_types: list[ApplicationIntegrationType] | None = None,
    contexts: list[InteractionContextType] | None = None,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY
) -> Callable[[InteractionCallback], ApplicationCommand]:
    return _base_command(
        ApplicationCommandType.CHAT_INPUT,
        name=name,
        scope=scope,
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
    nsfw: bool = False,
    integration_types: list[ApplicationIntegrationType] | None = None,
    contexts: list[InteractionContextType] | None = None,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY
) -> Callable[[InteractionCallback], ApplicationCommand]:
    return _base_command(
        ApplicationCommandType.MESSAGE,
        name=name,
        scope=scope,
        default_member_permissions=default_member_permissions,
        nsfw=nsfw,
        integration_types=integration_types,
        contexts=contexts
    )
