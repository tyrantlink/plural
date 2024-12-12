from pymongo import IndexModel
from datetime import datetime
from typing import ClassVar
from beanie import Document
from pydantic import Field


class GatewayEvent(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'gateway_events'
        validate_on_save = True
        indexes: ClassVar = [
            IndexModel('ts', expireAfterSeconds=30)
        ]

    id: str = Field(  # pyright: ignore #? unknown pyright rule
        description='the hash of the event body')
    instance: str = Field(
        description='the api instance (id of the MISSING variable)')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='the timestamp of the event')
