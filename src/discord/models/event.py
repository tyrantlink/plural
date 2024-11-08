from .enums import GatewayOpCode, GatewayEventName, ReactionType
from .base import RawBaseModel
from .message import Message
from .types import Snowflake
from pydantic import Field
from .member import Member
from .emoji import Emoji


__all__ = (
    'GatewayEvent',
    'MessageReactionAddEvent',
    'MessageCreateEvent',
    'MessageUpdateEvent',
)


class GatewayEvent(RawBaseModel):
    op_code: GatewayOpCode = Field(alias='op')
    data: dict = Field(alias='d')
    sequence: int | None = Field(alias='s')
    name: GatewayEventName | None = Field(alias='t')


class MessageReactionAddEvent(RawBaseModel):
    user_id: Snowflake
    channel_id: Snowflake
    message_id: Snowflake
    guild_id: Snowflake | None = None
    member: Member | None = None
    emoji: Emoji
    message_author_id: Snowflake | None = None
    burst: bool
    burst_colors: list[str] | None = None
    type: ReactionType


class MessageCreateEvent(Message):
    guild_id: Snowflake | None = None
    member: Member | None = None


class MessageUpdateEvent(MessageCreateEvent):
    ...
