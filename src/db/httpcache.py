from datetime import timedelta, datetime
from pymongo import IndexModel
from beanie import Document
from pydantic import Field
import logfire


class HTTPCache(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'httpcache'
        validate_on_save = True
        indexes = [  # ? 30 minute cache
            IndexModel('ts', expireAfterSeconds=60*30)
        ]

    id: str = Field(  # type: ignore
        description='the path of the request')
    status: int = Field(description='the status code of the request')
    data: dict | list | str | int | bool | float = Field(
        description='the json response of the request')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the request')

    @classmethod
    async def invalidate(cls, path: str) -> None:
        from src.discord.http import BASE_URL
        cache = await cls.find({'_id': f'{BASE_URL}{path}'}).delete()

        if cache and cache.deleted_count:
            logfire.debug(f'invalidated cache for {path}')
