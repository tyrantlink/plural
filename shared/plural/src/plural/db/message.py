from datetime import datetime, timedelta
from typing import ClassVar

from beanie import PydanticObjectId
from pydantic import Field

from .base import BaseDocument, ttl
from .enums import ProxyReason


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
    channel_id: int = Field(
        description='the channel id')
    member_id: PydanticObjectId = Field(
        description='the member id')
    reason: ProxyReason | str = Field(
        default=ProxyReason.NONE,
        description='the reason the message was proxied')
    webhook_id: int | None = Field(
        None,
        description='the webhook id of the message')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the message'
    )
