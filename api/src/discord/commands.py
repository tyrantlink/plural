from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from copy import deepcopy

from re import finditer

from src.core.http import request, Route, get_bot_id_from_token
from src.core.models import env

from plural.missing import Optional, Nullable, MISSING
from plural.db import ProxyMember, Usergroup
from plural.otel import span, cx

from .models import ApplicationCommand, InteractionCallback
from .enums import (
    ApplicationCommandOptionType,
    ApplicationIntegrationType,
    ApplicationCommandScope,
    InteractionContextType,
    ApplicationCommandType,
    Permission
)

if TYPE_CHECKING:
    from collections.abc import Callable


commands: dict[
    ApplicationCommandScope,
    dict[str, ApplicationCommand]
] = {
    ApplicationCommandScope.PRIMARY: {},
    ApplicationCommandScope.USERPROXY: {}
}

COMMAND_REF_MAP: dict[str, int] = {}

COMMAND_REF_PATTERN = r'{cmd_ref\[(.{1,32})\]}'


async def _put_all_commands(
    token: str,
    override_commands: dict[str, ApplicationCommand] | None = None
) -> None:
    application_id = get_bot_id_from_token(token)
    put_commands = (
        override_commands
        if override_commands is not None else
        commands[(
            ApplicationCommandScope.PRIMARY
            if application_id == env.application_id else
            ApplicationCommandScope.USERPROXY
        )]
    )

    await request(
        Route(
            'PUT',
            '/applications/{application_id}/commands',
            application_id=application_id,
            token=token),
        json=[
            command.as_payload()
            for command in put_commands.values()
        ]
    )


def _patch_reason(
    local: ApplicationCommand,
    live: ApplicationCommand
) -> list[str]:
    reasons = []

    if local.type != live.type:
        reasons.append(
            f'type ({local.type=} != {local.type=})'
        )

    if local.options != live.options:
        for local_option, live_option in zip(local.options or [], live.options or [], strict=False):
            if local_option != live_option:
                reasons.append(
                    f'options ({local_option=} != {live_option=})'
                )

    if local.default_member_permissions != live.default_member_permissions:
        reasons.append(
            f'default_member_permissions ({local.default_member_permissions=} != {live.default_member_permissions=})'
        )

    if local.nsfw != live.nsfw:
        reasons.append(
            f'nsfw ({local.nsfw=} != {live.nsfw=})'
        )

    if local.contexts != live.contexts:
        reasons.append(
            f'contexts ({local.contexts=} != {live.contexts=})'
        )

    return reasons


async def sync_commands(
    token: str,
    user_id: int | None = None
) -> None:
    global commands, COMMAND_REF_MAP

    application_id = get_bot_id_from_token(token)

    with span(f'sync_commands with {application_id}'):
        scope = (
            ApplicationCommandScope.PRIMARY
            if application_id == env.application_id else
            ApplicationCommandScope.USERPROXY
        )

        usergroup, member = None, None

        if token != env.bot_token:
            if user_id is None:
                raise ValueError(
                    'user_id must be provided when syncing userproxy commands'
                )

            usergroup = await Usergroup.get_by_user(
                user_id,
                False
            )

            member = await ProxyMember.find_one({
                'userproxy.bot_id': application_id
            }, ignore_cache=True)

        live_commands = {
            command['name']: ApplicationCommand(**command)
            for command in await request(Route(
                'GET',
                '/applications/{application_id}/commands',
                application_id=application_id,
                token=token
            ))
        }

        if scope == ApplicationCommandScope.PRIMARY:
            COMMAND_REF_MAP.update({
                command.name: command.id
                for command in live_commands.values()
            })

        local_commands = commands[scope]

        if (
            scope == ApplicationCommandScope.USERPROXY and
            'proxy' in local_commands and
            member and
            member.userproxy and
            usergroup
        ):
            local_commands = deepcopy(local_commands)

            options = local_commands['proxy'].options or []

            local_commands['proxy'].options = options[
                :len(options) - 10 + (
                    usergroup.userproxy_config.attachment_count
                )
            ]

            local_commands['proxy'].options[0].required = (
                usergroup.userproxy_config.required_message_parameter
            )

            if usergroup.userproxy_config.name_in_reply_command:
                command = local_commands.pop('Reply')
                command.name = f'Reply ({
                    member.name
                    if len(member.name) < 25 else
                    member.name[:21] + "..."})'
                local_commands[command.name] = command

            if member.userproxy.command:
                command = local_commands.pop('proxy')
                command.name = member.userproxy.command
                local_commands[command.name] = command

        cx().set_attribute(
            'commands', [
                command.name
                for command in local_commands.values()
            ]
        )

        if local_commands and not live_commands:
            with span('no live commands; registering all'):
                await _put_all_commands(
                    token,
                    local_commands
                )

            return

        updates: list[tuple[
            Literal['POST', 'PATCH', 'DELETE'],
            ApplicationCommand,
            list[str] | None
        ]] = []

        for command in local_commands.values():
            if command.name not in live_commands:
                updates.append(('POST', command, None))
                continue

            if live_commands[command.name] == command:
                continue

            command.id = live_commands[command.name].id

            updates.append((
                'PATCH',
                command,
                _patch_reason(
                    command,
                    live_commands[command.name]
                )
            ))

        for command in live_commands.values():
            if command.name not in local_commands:
                updates.append(('DELETE', command, None))

        if len(updates) > 4:
            with span('too many updates; registering all'):
                await _put_all_commands(
                    token,
                    local_commands
                )

            return

        for method, command, reason in updates:
            match method:
                case 'POST':
                    with span(f'registering /{command.name}'):
                        await request(
                            Route(
                                'POST',
                                '/applications/{application_id}/commands',
                                application_id=application_id,
                                token=token),
                            json=command.as_payload())
                case 'PATCH':
                    assert reason is not None
                    with span(
                        f'updating /{command.name}',
                        attributes={
                            'reasons': ', '.join(reason)
                        }
                    ):
                        await request(
                            Route(
                                'PATCH',
                                '/applications/{application_id}/commands/{command_id}',
                                application_id=application_id,
                                command_id=command.id,
                                token=token),
                            json=command.as_payload())
                case 'DELETE':
                    with span(f'deleting /{command.name}'):
                        await request(Route(
                            'DELETE',
                            '/applications/{application_id}/commands/{command_id}',
                            application_id=application_id,
                            command_id=command.id,
                            token=token
                        ))


def _base_command(
    type: ApplicationCommandType,
    name: str,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY,
    parent: Optional[ApplicationCommand | ApplicationCommand.Option] = MISSING,
    **kwargs  # noqa: ANN003
) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommand.Option]:
    def decorator(func: InteractionCallback) -> ApplicationCommand | ApplicationCommand.Option:
        if parent:
            parent.options = parent.options or []
            parent.options.append(
                ApplicationCommand.Option(
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
    options: Optional[list[ApplicationCommand.Option]] = MISSING,
    default_member_permissions: Nullable[Permission] = None,
    nsfw: bool = False,
    integration_types: Optional[list[ApplicationIntegrationType]] = MISSING,
    contexts: Optional[list[InteractionContextType]] = MISSING,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY,
    parent: Optional[ApplicationCommand] = MISSING
) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommand.Option]:
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


def SlashCommandGroup(  # noqa: N802
    name: str,
    description: str,
    default_member_permissions: Nullable[Permission] = None,
    nsfw: bool = False,
    integration_types: Optional[list[ApplicationIntegrationType]] = MISSING,
    contexts: Optional[list[InteractionContextType]] = MISSING,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY
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
    default_member_permissions: Nullable[Permission] = None,
    nsfw: bool = False,
    integration_types: Optional[list[ApplicationIntegrationType]] = MISSING,
    contexts: Optional[list[InteractionContextType]] = MISSING,
    scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY
) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommand.Option]:
    return _base_command(
        ApplicationCommandType.MESSAGE,
        name=name,
        description='',
        scope=scope,
        default_member_permissions=default_member_permissions,
        nsfw=nsfw,
        integration_types=integration_types,
        contexts=contexts
    )


def insert_cmd_ref(
    input: str
) -> str:
    for match in finditer(COMMAND_REF_PATTERN, input):
        command_id = COMMAND_REF_MAP.get(
            match.group(1).split(' ')[0],
            'COMMAND NOT FOUND')
        input = input.replace(
            match.group(0),
            f'</{match.group(1)}:{command_id}>',
            1
        )

    return input
