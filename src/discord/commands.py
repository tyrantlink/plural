from __future__ import annotations
from .models import ApplicationCommand, ApplicationCommandType, ApplicationCommandOption, ApplicationIntegrationType, InteractionContextType, Permission, InteractionCallback, ApplicationCommandScope, ApplicationCommandOptionType
from src.discord.http import Route, request, _get_bot_id
from src.db import ProxyMember, HTTPCache
from collections.abc import Callable
from src.models import project
from typing import Literal
from copy import deepcopy
import logfire


commands: dict[
    ApplicationCommandScope,
    dict[str, ApplicationCommand]
] = {
    ApplicationCommandScope.PRIMARY: {},
    ApplicationCommandScope.USERPROXY: {}
}
# ? i don't care enough to implement guild commands


async def _put_all_commands(
    token: str,
    override_commands: dict[str, ApplicationCommand] | None = None
) -> None:
    application_id = _get_bot_id(token)
    put_commands = (
        override_commands
        if override_commands is not None else
        commands[(
            ApplicationCommandScope.PRIMARY
            if application_id == project.application_id else
            ApplicationCommandScope.USERPROXY
        )])

    await request(
        Route(
            'PUT',
            '/applications/{application_id}/commands',
            application_id=application_id
        ),
        token=token,
        json=[
            command._as_registration_dict()
            for command in put_commands.values()
        ]
    )


def _patch_reason(local_command: ApplicationCommand, live_command: ApplicationCommand) -> list[str]:
    reasons = []

    if local_command.type != live_command.type:
        reasons.append(f'type ({local_command.type=} != {live_command.type=})')

    if local_command.options != live_command.options:
        for local_option, live_option in zip(local_command.options or [], live_command.options or []):
            if local_option != live_option:
                reasons.append(f'options ({local_option=} != {live_option=})')

    if local_command.default_member_permissions != live_command.default_member_permissions:
        reasons.append(
            f'default_member_permissions ({local_command.default_member_permissions=} != {
                live_command.default_member_permissions=})')

    if local_command.nsfw != live_command.nsfw:
        reasons.append(f'nsfw ({local_command.nsfw=} != {live_command.nsfw=})')

    if local_command.contexts != live_command.contexts:
        reasons.append(f'contexts ({local_command.contexts=} != {
                       live_command.contexts=})')

    return reasons


async def _sync_commands(
    token: str | None = None
) -> None:
    global commands
    application_id = _get_bot_id(token or project.bot_token)

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

    if token != project.bot_token:
        member = await ProxyMember.find_one({'userproxy.bot_id': application_id})

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

    if scope == ApplicationCommandScope.USERPROXY:
        # ? userproxy edit is deprecated, will be removed from codebase in the future
        working_commands.pop('edit', None)

    # ? inject custom userproxy 'proxy' command name
    if scope == ApplicationCommandScope.USERPROXY and 'proxy' in working_commands:
        working_commands = deepcopy(working_commands)

        if member and member.userproxy and member.userproxy.command:
            command = working_commands.pop('proxy')
            command.name = member.userproxy.command
            working_commands[command.name] = command

        working_commands.update(commands[ApplicationCommandScope.USERPROXY])

    if working_commands != live_commands:
        await HTTPCache.invalidate(f'/applications/{application_id}/commands')

    if working_commands and not live_commands:
        logfire.debug('no commands found on discord, registering all')
        await _put_all_commands(
            token
        )
        return

    updates: list[
        tuple[
            Literal['POST', 'PATCH', 'DELETE'],
            ApplicationCommand,
            list[str] | None
        ]
    ] = []

    for command in working_commands.values():
        if command.name not in live_commands:
            updates.append(('POST', command, None))
            continue

        if live_commands[command.name] != command:
            command.id = live_commands[command.name].id
            updates.append((
                'PATCH',
                command,
                _patch_reason(command, live_commands[command.name])
            ))

    for command in live_commands.values():
        if command.name not in working_commands:
            updates.append(('DELETE', command, None))

    if len(updates) > 4:
        logfire.debug('too many updates, registering all')
        await _put_all_commands(
            token
        )
        return

    for method, command, reason in updates:
        match method:
            case 'POST':
                logfire.debug(
                    'registering {command_name}', command_name=command.name)
                await request(
                    Route(
                        'POST',
                        '/applications/{application_id}/commands',
                        application_id=application_id
                    ),
                    json=command._as_registration_dict(),
                    token=token
                )
            case 'PATCH':
                logfire.debug(
                    'updating {command_name} ({reason})',
                    command_name=command.name,
                    reason=', '.join(reason or [])
                )
                await request(
                    Route(
                        'PATCH',
                        '/applications/{application_id}/commands/{command_id}',
                        application_id=application_id,
                        command_id=command.id
                    ),
                    json=command._as_registration_dict(),
                    token=token
                )
            case 'DELETE':
                logfire.debug(
                    'deleting {command_name}', command_name=command.name)
                await request(
                    Route(
                        'DELETE',
                        '/applications/{application_id}/commands/{command_id}',
                        application_id=application_id,
                        command_id=command.id
                    ),
                    token=token
                )


async def sync_commands(
    token: str | None = None
) -> None:
    application_id = _get_bot_id(token or project.bot_token)
    if project.logfire_token:
        with logfire.span('sync_commands with {application_id}', application_id=application_id):
            await _sync_commands(token)
        return

    await _sync_commands(token)


def _base_command(
    type: ApplicationCommandType,
    name: str,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY,
    parent: ApplicationCommand | ApplicationCommandOption | None = None,
    **kwargs
) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommandOption]:
    def decorator(func: InteractionCallback) -> ApplicationCommand | ApplicationCommandOption:
        if parent:
            parent.options = parent.options or []
            parent.options.append(
                ApplicationCommandOption(
                    type=ApplicationCommandOptionType.SUB_COMMAND,
                    name=name,
                    callback=func,
                    **kwargs
                )
            )

            return parent

        command = ApplicationCommand(
            type=type,
            name=name,
            callback=func,
            **kwargs
        )

        commands[scope][name] = command

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
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY,
    parent: ApplicationCommand | None = None
) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommandOption]:
    return _base_command(
        ApplicationCommandType.CHAT_INPUT,
        name=name,
        scope=scope,
        description=description,
        options=options,
        default_member_permissions=default_member_permissions,
        nsfw=nsfw,
        integration_types=integration_types,
        contexts=contexts,
        parent=parent
    )


def SlashCommandGroup(
    name: str,
    description: str,
    default_member_permissions: Permission | None = None,
    nsfw: bool = False,
    integration_types: list[ApplicationIntegrationType] | None = None,
    contexts: list[InteractionContextType] | None = None,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY,
) -> ApplicationCommand:
    command = ApplicationCommand(
        type=ApplicationCommandType.CHAT_INPUT,
        name=name,
        description=description,
        default_member_permissions=default_member_permissions,
        nsfw=nsfw,
        integration_types=integration_types,
        contexts=contexts,
        callback=None
    )

    commands[scope][name] = command

    return command


def message_command(
    name: str,
    default_member_permissions: Permission | None = None,
    nsfw: bool = False,
    integration_types: list[ApplicationIntegrationType] | None = None,
    contexts: list[InteractionContextType] | None = None,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY
) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommandOption]:
    return _base_command(
        ApplicationCommandType.MESSAGE,
        name=name,
        scope=scope,
        default_member_permissions=default_member_permissions,
        nsfw=nsfw,
        integration_types=integration_types,
        contexts=contexts
    )
