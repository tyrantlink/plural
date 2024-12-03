from datetime import timedelta, datetime
from pymongo import IndexModel
from beanie import Document
from pydantic import Field


class GatewayEvent(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'gateway_events'
        use_cache = True
        validate_on_save = True
        cache_expiration_time = timedelta(seconds=30)
        indexes = [
            IndexModel('ts', expireAfterSeconds=30)
        ]

    id: str = Field(  # type: ignore
        description='the hash of the event body')
    instance: str = Field(
        description='the api instance (id of the MISSING variable)')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the event')
