from beanie import Document, PydanticObjectId
from datetime import timedelta, datetime
from pymongo import IndexModel
from pydantic import Field


class UserProxyInteraction(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'userproxy_interaction'
        use_cache = True
        validate_on_save = True
        cache_expiration_time = timedelta(minutes=15)
        indexes = [
            'message_id',
            'application_id',
            # ? tokens expire after 15 minutes
            IndexModel('ts', expireAfterSeconds=880)
        ]

    id: PydanticObjectId = Field(  # type: ignore
        default_factory=PydanticObjectId)
    application_id: int = Field(
        description='the id of the application')
    message_id: int = Field(
        description='the original id of the message')
    token: str = Field(description='the token of the interaction')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the message')
