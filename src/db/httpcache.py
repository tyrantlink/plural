from datetime import timedelta, datetime
from pymongo import IndexModel
from beanie import Document
from pydantic import Field


class HTTPCache(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'httpcache'
        use_cache = True
        validate_on_save = True
        cache_expiration_time = timedelta(minutes=1)
        indexes = [
            'path',
            IndexModel('ts', expireAfterSeconds=60*60*4)
        ]

    url: str = Field(description='the path of the request')
    data: dict = Field(description='the json response of the request')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the request')
