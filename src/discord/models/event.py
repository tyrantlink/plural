from __future__ import annotations
from .enums import GatewayOpCode, GatewayEventName, ReactionType
from src.discord.types import Snowflake
from .base import RawBaseModel
from .message import Message
from pydantic import Field
from .member import Member
from .emoji import Emoji


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


class MessageCreateEvent(Message, RawBaseModel):
    guild_id: Snowflake | None = None
    member: Member | None = None

    async def populate(self) -> None:
        await super().populate()

        if self.guild_id is not None and self.author is not None and self.webhook_id is None:
            self.member = await Member.fetch(
                self.guild_id,
                self.author.id
            )


class MessageUpdateEvent(MessageCreateEvent):
    ...
