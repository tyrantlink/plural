from __future__ import annotations
from beanie import Document, PydanticObjectId
from typing import TYPE_CHECKING, ClassVar
from pydantic import Field, BaseModel
from pymongo import IndexModel
from datetime import datetime
from .enums import ReplyType
from io import BytesIO

if TYPE_CHECKING:
    from src.discord.http import File


class Reply(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'replies'
        validate_on_save = True
        use_state_management = True
        indexes: ClassVar = [
            ('bot_id', 'channel'),  # ? compound index
            IndexModel('ts', expireAfterSeconds=300)
        ]

    class Attachment(BaseModel):
        url: str = Field(description='the url of the attachment')
        filename: str = Field(description='the filename of the attachment')
        description: str | None = Field(
            None, description='the description of the attachment')

        async def as_file(self) -> File:
            from src.discord.http import File, get_from_cdn
            return File(
                BytesIO(await get_from_cdn(self.url)),
                filename=self.filename,
                description=self.description,
                spoiler=self.filename.startswith('SPOILER_')
            )

    class Author(BaseModel):
        id: int = Field(description='the author id')
        username: str = Field(description='the author username')
        avatar: str | None = Field(description='the author avatar hash')

    id: PydanticObjectId = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        default_factory=PydanticObjectId)
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
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp for the reply; used for ttl')
