from datetime import datetime, timedelta
from typing import ClassVar

from beanie import PydanticObjectId
from pydantic import Field

from .base import BaseDocument, ttl


class Interaction(BaseDocument):
    class Settings:
        name = 'interactions'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            'message_id',
            'application_id',
            'channel_id',
            ttl(minutes=14, seconds=45)
        ]

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the internal id of the interaction')
    author_id: int = Field(
        description='the author id')
    bot_id: int = Field(
        description='the id of the userproxy')
    message_id: int = Field(
        description='the id of the message')
    channel_id: int = Field(
        description='the channel id')
    token: str = Field(
        description='the interaction token')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the interaction'
    )
