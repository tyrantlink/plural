from datetime import datetime, timedelta
from typing import ClassVar

from beanie import PydanticObjectId
from pydantic import Field

from .base import BaseDocument, ttl


class ProxyLog(BaseDocument):
    class Settings:
        name = 'proxy_logs'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            ttl(minutes=1)
        ]

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId)
    author_id: int | None = Field(
        description='author user id')
    message_id: int | None = Field(
        description='original message id')
    author_name: str | None = Field(
        description='author name')
    channel_id: int | None = Field(
        description='channel id')
    content: str | None = Field(
        description='sha256 hash of the message content')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp'
    )
