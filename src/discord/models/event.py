from __future__ import annotations
from .enums import GatewayOpCode, GatewayEventName, ReactionType, WebhookEventType, EventType, ApplicationIntegrationType
from src.models import MISSING, MissingOr
from src.discord.types import Snowflake
from src.errors import NotFound
from .base import RawBaseModel
from datetime import datetime
from .message import Message
from pydantic import Field
from .member import Member
from .guild import Guild
from .emoji import Emoji
from .user import User


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

        if not (
            self.guild_id is not None and
            self.author is not None and
            self.webhook_id is None
        ):
            return None

        try:
            self.member = await Member.fetch(
                self.guild_id,
                self.author.id)
        except NotFound:
            return None


class MessageUpdateEvent(MessageCreateEvent):
    ...


class ApplicationAuthorizedEvent(RawBaseModel):
    integration_type: MissingOr[ApplicationIntegrationType] = MISSING
    user: User
    scopes: list[str]
    guild: MissingOr[Guild] = MISSING


class WebhookEventBody(RawBaseModel):
    type: EventType
    timestamp: datetime
    data: MissingOr[ApplicationAuthorizedEvent] = MISSING


class WebhookEvent(RawBaseModel):
    version: int
    application_id: Snowflake
    type: WebhookEventType
    event: MissingOr[WebhookEventBody] = MISSING
