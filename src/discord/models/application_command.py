from __future__ import annotations
from .enums import ApplicationCommandType, ApplicationCommandOptionType, ChannelType, ApplicationIntegrationType, InteractionContextType, EntryPointCommandHandlerType
from collections.abc import Callable, Awaitable
from .interaction import Interaction
from .base import RawBaseModel
from src.discord.types import Snowflake
from pydantic import Field

__all__ = (
    'ApplicationCommandOptionChoice',
    'ApplicationCommandOption',
    'ApplicationCommand',
)


COMMAND_NAME_PATTERN = r'^[-_\p{L}\p{N}\p{sc=Deva}\p{sc=Thai}]{1,32}$'


class ApplicationCommandOptionChoice(RawBaseModel):
    ...  # !


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


class ApplicationCommand(RawBaseModel):
    id: Snowflake
    type: ApplicationCommandType
    application_id: Snowflake
    guild_id: Snowflake | None = None
    name: str = Field(pattern=COMMAND_NAME_PATTERN)
    name_localizations: dict[str, str] = Field(default_factory=dict)
    description: str = Field(max_length=100)
    description_localizations: dict[str, str] = Field(default_factory=dict)
    options: list[ApplicationCommandOption] | None = None
    default_member_permissions: str | None = None  # ! make this a Permission object
    dm_permission: bool | None = None  # deprecated
    default_permission: bool | None = None  # deprecated
    nsfw: bool | None = False
    integration_types: list[ApplicationIntegrationType] | None = None
    contexts: list[InteractionContextType] | None = None
    version: Snowflake
    handler: EntryPointCommandHandlerType | None = None
    # ? library stuff
    callback: Callable[[Interaction], Awaitable[None]] | None = None
