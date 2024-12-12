from pymongo import IndexModel
from datetime import datetime
from beanie import Document
from typing import ClassVar
from pydantic import Field


class ApiToken(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'api_tokens'
        validate_on_save = True
        use_state_management = True
        indexes: ClassVar = [
            IndexModel('ts', expireAfterSeconds=60*60*8)
        ]

    id: int = Field(  # pyright: ignore #? unknown pyright rule
        description='user id')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp of validation'
    )
