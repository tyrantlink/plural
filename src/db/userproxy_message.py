from beanie import Document, PydanticObjectId
from datetime import timedelta, datetime
from pymongo import IndexModel
from pydantic import Field


class UserProxyMessage(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'userproxy_messages'
        validate_on_save = True
        cache_expiration_time = timedelta(minutes=15)
        indexes = [
            'message_id',
            # ? tokens expire after 15 minutes
            IndexModel('ts', expireAfterSeconds=880)
        ]

    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    message_id: int = Field(
        description='the original id of the message')
    token: str = Field(description='the token of the interaction')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the message')
