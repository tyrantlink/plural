from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Protocol

from pydantic import Field

from plural.missing import MISSING

from src.discord.models.base import RawBaseModel, PydanticArbitraryType

from src.discord.enums import (
    ApplicationCommandOptionType,
    ApplicationCommandScope,
    ApplicationCommandType,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from plural.missing import Optional, Nullable
    from src.discord.types import Snowflake

    from .interaction import Interaction

    from src.discord.enums import (
        ApplicationIntegrationType,
        InteractionContextType,
        ChannelType,
        Permission
    )


__all__ = (
    'ApplicationCommand',
    'InteractionCallback',
)


class InteractionCallback(Protocol):
    async def __call__(
        self,
        interaction: Interaction,
        *args,  # noqa: ANN002
        **kwargs  # noqa: ANN003
    ) -> None:
        ...


class CommandMixin:
    callback: Optional[Annotated[
        InteractionCallback,
        PydanticArbitraryType
    ]] = Field(None, exclude=True)

    def command(
        self,
        name: str,
        description: str,
        options: Optional[list[ApplicationCommand.Option]] = MISSING,
        default_member_permissions: Nullable[Permission] = None,
        nsfw: bool = False,
        integration_types: Optional[list[ApplicationIntegrationType]] = MISSING,
        contexts: Optional[list[InteractionContextType]] = MISSING,
        scope: ApplicationCommandScope = ApplicationCommandScope.PRIMARY
    ) -> Callable[[InteractionCallback], ApplicationCommand | ApplicationCommand.Option]:
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


class ApplicationCommand(RawBaseModel, CommandMixin):
    class Option(RawBaseModel, CommandMixin):
        class Choice(RawBaseModel):
            name: str
            name_localizations: Optional[Nullable[dict[str, str]]]
            value: str | int | float

        def __eq__(self, value: object) -> bool:
            return (
                isinstance(value, ApplicationCommand.Option) and
                value.type == self.type and
                value.name == self.name and
                value.description == self.description and
                (value.required or False) == (self.required or False) and
                value.choices == self.choices and
                value.options == self.options and
                value.channel_types == self.channel_types and
                value.min_value == self.min_value and
                value.max_value == self.max_value and
                value.min_length == self.min_length and
                value.max_length == self.max_length and
                value.autocomplete == self.autocomplete
            )

        type: ApplicationCommandOptionType
        """Type of option"""
        name: str
        """1-32 character name"""
        name_localizations: Optional[Nullable[dict[str, str]]]
        """Localization dictionary for `name` field. Values follow the same restrictions as `name`"""
        description: str
        """1-100 character description"""
        description_localizations: Optional[Nullable[dict[str, str]]]
        """Localization dictionary for `description` field. Values follow the same restrictions as `description`"""
        required: Optional[bool]
        """Whether the parameter is required or optional, default `false`"""
        choices: Optional[list[ApplicationCommand.Option.Choice]]
        """Choices for the user to pick from, max 25"""
        options: Optional[list[ApplicationCommand.Option]]
        """If the option is a subcommand or subcommand group type, these nested options will be the parameters or subcommands respectively; up to 25"""
        channel_types: Optional[list[ChannelType]]
        """The channels shown will be restricted to these types"""
        min_value: Optional[int]
        """The minimum value permitted"""
        max_value: Optional[int]
        """The maximum value permitted"""
        min_length: Optional[int]
        """The minimum allowed length (minimum of `0`, maximum of `6000`)"""
        max_length: Optional[int]
        """The maximum allowed length (minimum of `1`, maximum of `6000`)"""
        autocomplete: Optional[bool]
        """If autocomplete interactions are enabled for this option"""

    id: Optional[Snowflake]
    """Unique ID of command"""
    type: Optional[ApplicationCommandType]
    """Type of command, defaults to `1` (ApplicationCommandType.CHAT_INPUT)"""
    application_id: Optional[Snowflake]
    """ID of the parent application"""
    guild_id: Optional[Snowflake]
    """Guild ID of the command, if not global"""
    name: str
    """Name of command, 1-32 characters"""
    name_localizations: Optional[Nullable[dict[str, str]]]
    """Localization dictionary for `name` field. Values follow the same restrictions as `name`"""
    description: str
    """Description for `CHAT_INPUT` commands, 1-100 characters. Empty string for `USER` and `MESSAGE` commands"""
    description_localizations: Optional[Nullable[dict[str, str]]]
    """Localization dictionary for `description` field. Values follow the same restrictions as `description`"""
    options: Optional[list[ApplicationCommand.Option]] = MISSING
    """Parameters for the command, max of 25"""
    default_member_permissions: Nullable[Permission]
    """Set of permissions represented as a bit set"""
    nsfw: bool
    """Indicates whether the command is age-restricted, defaults to `false`"""
    integration_types: Optional[list[ApplicationIntegrationType]]
    """Installation contexts where the command is available, only for globally-scoped commands. Defaults to your app's configured contexts"""
    contexts: Nullable[list[InteractionContextType]]
    """Interaction context(s) where the command can be used, only for globally-scoped commands. By default, all interaction context types included for new commands."""
    version: Optional[Snowflake]
    # CommandHandlerType, only for PRIMARY_ENTRY_POINT commands
    handler: Optional[int]

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ApplicationCommand) and
            value.type == self.type and
            value.name == self.name and
            value.name_localizations == self.name_localizations and
            value.description == self.description and
            value.description_localizations == self.description_localizations and
            value.options == self.options and
            value.default_member_permissions == self.default_member_permissions and
            value.nsfw == self.nsfw and
            value.integration_types == self.integration_types and
            value.contexts == self.contexts
        )

    def create_subgroup(
        self,
        name: str,
        description: str,
    ) -> ApplicationCommand.Option:
        subgroup = ApplicationCommand.Option(
            type=ApplicationCommandOptionType.SUB_COMMAND_GROUP,
            name=name,
            description=description
        )

        self.options = self.options or []
        self.options.append(subgroup)

        return subgroup
