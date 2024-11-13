from __future__ import annotations
from .enums import ApplicationCommandType, ApplicationCommandOptionType, ChannelType, ApplicationIntegrationType, InteractionContextType, EntryPointCommandHandlerType, Permission, ApplicationCommandScope
from typing import Annotated, Callable, TYPE_CHECKING
from .base import RawBaseModel, PydanticArbitraryType
from .interaction import InteractionCallback
from src.discord.types import Snowflake
from pydantic import Field


COMMAND_NAME_PATTERN = r'^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$'


class ApplicationCommandOptionChoice(RawBaseModel):
    name: str
    name_localizations: dict[str, str] | None = None
    value: str | int | float


class ApplicationCommandOption(RawBaseModel):
    type: ApplicationCommandOptionType
    name: str = Field(pattern=COMMAND_NAME_PATTERN)
    name_localizations: dict[str, str] | None = None
    description: str = Field(max_length=100)
    description_localizations: dict[str, str] | None = None
    required: bool = False
    choices: list[ApplicationCommandOptionChoice] | None = None
    options: list[ApplicationCommandOption] | None = None
    channel_types: list[ChannelType] | None = None
    min_value: int | None = None
    max_value: int | None = None
    min_length: int | None = None
    max_length: int | None = None
    autocomplete: bool = False
    # ? library stuff
    if TYPE_CHECKING:
        callback: Annotated[InteractionCallback,
                            PydanticArbitraryType] | None = None
    else:
        callback: Annotated[InteractionCallback,
                            PydanticArbitraryType] | None = Field(None, exclude=True)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ApplicationCommandOption) and
            value.type == self.type and
            value.name == self.name and
            value.description == self.description and
            value.required == self.required and
            value.choices == self.choices and
            value.options == self.options and
            value.channel_types == self.channel_types and
            value.min_value == self.min_value and
            value.max_value == self.max_value and
            value.min_length == self.min_length and
            value.max_length == self.max_length and
            value.autocomplete == self.autocomplete
        )

    def command(
        self,
        name: str,
        description: str,
        options: list[ApplicationCommandOption] | None = None,
        default_member_permissions: Permission | None = None,
        nsfw: bool = False,
        integration_types: list[ApplicationIntegrationType] | None = None,
        contexts: list[InteractionContextType] | None = None,
        scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY
    ) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommandOption]:
        from src.discord.commands import _base_command
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
            parent=self
        )


class ApplicationCommand(RawBaseModel):
    id: Snowflake | None = None
    type: ApplicationCommandType | ApplicationCommandOptionType
    application_id: Snowflake | None = None
    guild_id: Snowflake | None = None
    name: str
    name_localizations: dict[str, str] | None = None
    description: str | None = None
    description_localizations: dict[str, str] | None = None
    options: list[ApplicationCommandOption] | None = None
    default_member_permissions: Permission | None = None
    dm_permission: bool | None = None  # deprecated
    default_permission: bool | None = None  # deprecated
    nsfw: bool | None = None
    integration_types: list[ApplicationIntegrationType] | None = None
    contexts: list[InteractionContextType] | None = None
    version: Snowflake | None = None
    handler: EntryPointCommandHandlerType | None = None
    # ? library stuff
    callback: Annotated[InteractionCallback,
                        PydanticArbitraryType] | None = Field(None, exclude=True)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ApplicationCommand) and
            value.type == self.type and
            value.name == self.name and
            value.options == self.options and
            value.default_member_permissions == self.default_member_permissions and
            value.nsfw == self.nsfw and
            value.contexts == self.contexts
        )

    def _as_registration_dict(self) -> dict:
        json: dict = {
            'name': self.name,
            'description': self.description,
            'type': self.type.value,
        }

        if self.type == ApplicationCommandType.CHAT_INPUT:
            json['options'] = [
                option.model_dump(mode='json')
                for option in self.options or []
            ]

        if self.name_localizations is not None:
            json['name_localizations'] = self.name_localizations

        if self.description_localizations is not None:
            json['description_localizations'] = self.description_localizations

        if self.default_member_permissions is not None:
            json['default_member_permissions'] = str(
                self.default_member_permissions.value)

        contexts = set(self.contexts or [])

        if self.dm_permission is not None:
            contexts.add(InteractionContextType.BOT_DM)
            contexts.add(InteractionContextType.PRIVATE_CHANNEL)

        if self.default_permission is not None:
            json['default_permission'] = self.default_permission

        if self.nsfw is not None:
            json['nsfw'] = self.nsfw

        if self.integration_types is not None:
            json['integration_types'] = [
                integration_type.value
                for integration_type in self.integration_types
            ]

        if contexts:
            json['contexts'] = [
                context.value
                for context in contexts
            ]

        return json

    def command(
        self,
        name: str,
        description: str,
        options: list[ApplicationCommandOption] | None = None,
        default_member_permissions: Permission | None = None,
        nsfw: bool = False,
        integration_types: list[ApplicationIntegrationType] | None = None,
        contexts: list[InteractionContextType] | None = None,
        scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY
    ) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommandOption]:
        from src.discord.commands import _base_command
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
            parent=self
        )

    def create_subgroup(
        self,
        name: str,
        description: str,
    ) -> ApplicationCommandOption:
        subgroup = ApplicationCommandOption(
            type=ApplicationCommandOptionType.SUB_COMMAND_GROUP,
            name=name,
            description=description
        )

        self.options = self.options or []
        self.options.append(subgroup)

        return subgroup
