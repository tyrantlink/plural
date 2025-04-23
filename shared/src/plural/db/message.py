from datetime import datetime, timedelta, UTC
from typing import ClassVar

from beanie import PydanticObjectId
from pydantic import Field

from .base import BaseDocument, ttl


class Message(BaseDocument):
    class Settings:
        name = 'messages'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            'original_id',
            'proxy_id',
            'author_id',
            ('user', ('ts', -1)),
            ttl(days=7)
        ]

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the internal id of the message')
    original_id: int | None = Field(
        description='the id of the original message; None if userproxy message or sent through api')
    proxy_id: int = Field(
        description='the id of the proxy message')
    author_id: int = Field(
        description='the author id')
    user: PydanticObjectId = Field(
        description='the usergroup author id')
    channel_id: int = Field(
        description='the channel id')
    member_id: PydanticObjectId = Field(
        description='the member id')
    reason: str = Field(
        default='no reason given, this should never be seen',
        description='the reason the message was proxied')
    webhook_id: int | None = Field(
        None,
        description='the webhook id of the message')
    reference_id: int | None = Field(
        None,
        description='the id of the referenced message; None if not a reply')
    bot_id: int | None = Field(
        None,
        description='the bot id of the message')
    interaction_token: str | None = Field(
        None,
        description='the interaction token of the message')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the message'
    )

    @property
    def expired(self) -> bool:
        return (
            self.ts.replace(tzinfo=UTC) + timedelta(minutes=14, seconds=30)
        ) < datetime.now(UTC)
