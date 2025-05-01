from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from src.discord.types import Snowflake
    from plural.missing import Optional

    from src.discord.enums import (
        ApplicationCommandOptionType,
        ApplicationCommandType,
        ComponentType
    )

    from src.discord.models.component import ActionRow
    from src.discord.models.resolved import Resolved


class ApplicationCommandInteractionData(RawBaseModel):
    class Option(RawBaseModel):
        name: str
        """Name of the parameter"""
        type: ApplicationCommandOptionType
        """Value of application command option type"""
        value: Optional[str | int | float | bool]
        """Value of the option resulting from user input"""
        options: Optional[list[ApplicationCommandInteractionData.Option]]
        """Present if this option is a group or subcommand"""
        focused: Optional[bool]
        """`true` if this option is the currently focused option for autocomplete"""

    id: Snowflake
    """`ID` of the invoked command"""
    name: str
    """`name` of the invoked command"""
    type: ApplicationCommandType
    """`type` of the invoked command"""
    resolved: Optional[Resolved]
    """Converted users + roles + channels + attachments"""
    options: Optional[list[Option]]
    """Params + values from the user"""
    guild_id: Optional[Snowflake]
    """ID of the guild the command is registered to"""
    target_id: Optional[Snowflake]
    """ID of the user or message targeted by a user or message command"""


class MessageComponentInteractionData(RawBaseModel):
    custom_id: str
    """`custom_id` of the component"""
    component_type: ComponentType
    """`type` of the component"""
    values: Optional[list]  # ? list[SelectOption]
    """Values the user selected in a select menu component"""
    resolved: Optional[Resolved]
    """Resolved entities from selected options"""


class ModalSubmitInteractionData(RawBaseModel):
    custom_id: str
    """`custom_id` of the modal"""
    components: list[ActionRow]
    """Values submitted by the user"""


type InteractionData = ApplicationCommandInteractionData | MessageComponentInteractionData | ModalSubmitInteractionData
