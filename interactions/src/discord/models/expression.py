from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from plural.missing import Optional, Nullable

    from src.discord.types import Snowflake
    from src.discord.enums import StickerType, StickerFormatType

    from .user import User


__all__ = (
    'Emoji',
    'Reaction',
    'Sticker',
    'StickerItem',
)


class Emoji(RawBaseModel):
    id: Nullable[Snowflake]
    """emoji id"""
    name: Nullable[str]
    """emoji name (can be null only in reaction emoji objects)"""
    roles: Optional[list[Snowflake]]
    """roles allowed to use this emoji"""
    user: Optional[User]
    """user that created this emoji"""
    require_colons: Optional[bool]
    """whether this emoji must be wrapped in colons"""
    managed: Optional[bool]
    """whether this emoji is managed"""
    animated: Optional[bool]
    """whether this emoji is animated"""
    available: Optional[bool]
    """whether this emoji can be used, may be false due to loss of Server Boosts"""


class Reaction(RawBaseModel):
    class CountDetails(RawBaseModel):
        burst: int
        """Count of super reactions"""
        normal: int
        """Count of normal reactions"""

    count: int
    """Total number of times this emoji has been used to react (including super reacts)"""
    count_details: CountDetails
    """Reaction count details object"""
    me: bool
    """Whether the current user reacted using this emoji"""
    me_burst: bool
    """Whether the current user super-reacted using this emoji"""
    emoji: Emoji
    """emoji information"""
    burst_colors: list[str]
    """HEX colors used for super reaction"""


class Sticker(RawBaseModel):
    id: Snowflake
    """id of the sticker"""
    pack_id: Optional[Snowflake]
    """for standard stickers, id of the pack the sticker is from"""
    name: str
    """name of the sticker"""
    description: Nullable[str]
    """description of the sticker"""
    tags: str
    """autocomplete/suggestion tags for the sticker (max 200 characters)"""
    type: StickerType
    """type of sticker"""
    format_type: StickerFormatType
    """type of sticker format"""
    available: Optional[bool]
    """whether this guild sticker can be used, may be false due to loss of Server Boosts"""
    guild_id: Optional[Snowflake]
    """id of the guild that owns this sticker"""
    user: Optional[User]
    """the user that uploaded the guild sticker"""
    sort_value: Optional[int]
    """the standard sticker's sort order within its pack"""


class StickerItem(RawBaseModel):
    id: Snowflake
    """id of the sticker"""
    name: str
    """name of the sticker"""
    format_type: StickerFormatType
    """type of sticker format"""
