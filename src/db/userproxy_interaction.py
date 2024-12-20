from beanie import Document, PydanticObjectId
from pymongo import IndexModel
from datetime import datetime
from typing import ClassVar
from pydantic import Field


class UserProxyInteraction(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'userproxy_interaction'
        validate_on_save = True
        indexes: ClassVar = [
            'message_id',
            'application_id',
            'channel_id',
            # ? tokens expire after 15 minutes
            IndexModel('ts', expireAfterSeconds=880)
        ]

    id: PydanticObjectId = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        default_factory=PydanticObjectId)
    author_id: int = Field(description='the id of the author')
    application_id: int = Field(
        description='the id of the application')
    message_id: int = Field(
        description='the original id of the message')
    channel_id: int = Field(
        description='the channel id of the message')
    token: str = Field(description='the token of the interaction')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the message')
