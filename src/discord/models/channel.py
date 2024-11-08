from .base import RawBaseModel
from .types import Snowflake
from .enums import ChannelType

__all__ = (
    'ChannelMention',
    'Channel',
)


class ChannelMention(RawBaseModel):
    id: Snowflake
    guild_id: Snowflake
    type: ChannelType
    name: str


class Channel(RawBaseModel):
    ...
