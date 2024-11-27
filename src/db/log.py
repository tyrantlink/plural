from beanie import Document, PydanticObjectId
from datetime import datetime, timedelta
from pymongo import IndexModel
from pydantic import Field


class Log(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'logs'
        use_cache = True
        validate_on_save = True
        use_state_management = True
        cache_expiration_time = timedelta(seconds=60)
        indexes = [
            IndexModel('ts', expireAfterSeconds=60)
        ]

    id: PydanticObjectId = Field(  # type: ignore
        default_factory=PydanticObjectId)
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp for the log; used for ttl')
    author_id: int | None = None
    message_id: int | None = None
    author_name: str | None = None
    channel_id: int | None = None
    content: str | None = None
