from beanie import Document, PydanticObjectId
from datetime import timedelta, datetime
from pydantic import Field


class Message(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'messages'
        use_cache = True
        validate_on_save = True
        use_state_management = True
        cache_expiration_time = timedelta(minutes=30)
        indexes = ['original_id', 'proxy_id']

    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    original_id: int = Field(description='the original id of the message')
    proxy_id: int = Field(description='the proxy id of the message')
    author_id: int = Field(description='the author id of the message')
    ts: datetime = Field(
        default_factory=datetime.now,
        description='the timestamp of the message')
