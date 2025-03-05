from datetime import datetime, timedelta
from typing import ClassVar

from pydantic import Field, BaseModel
from beanie import PydanticObjectId

from .base import BaseDocument, ttl
from .enums import ReplyType


class Reply(BaseDocument):
    class Settings:
        name = 'replies'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            ttl()  # ? expire immediately
        ]

    class Attachment(BaseModel):
        url: str = Field(description='the url of the attachment')
        filename: str = Field(description='the filename of the attachment')
        description: str | None = Field(
            None, description='the description of the attachment')

    class Author(BaseModel):
        id: int = Field(description='the author id')
        global_name: str | None = Field(description='the author global name')
        username: str = Field(description='the author username')
        avatar: str | None = Field(description='the author avatar hash')

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the id of the reply')
    type: ReplyType = Field(description='the type of the reply')
    bot_id: int = Field(description='bot id')
    channel: int = Field(description='the channel id of the reply')
    content: str | None = Field(description='the userproxy content')
    message_id: int | None = Field(
        description='the message id (if type is ReplyType.REPLY)')
    author: Author | None = Field(
        description='the author (if type is ReplyType.REPLY)')
    attachments: list[Attachment] = Field(
        description='the message attachment')
    webhook_id: int | None = Field(
        description='the webhook id (if type is ReplyType.REPLY)')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp for the reply; used for ttl')
