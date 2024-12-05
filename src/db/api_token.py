from pymongo import IndexModel
from datetime import datetime
from beanie import Document
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
        indexes = [
            IndexModel('ts', expireAfterSeconds=60*60*8)
        ]

    id: int = Field(description='user id')  # type: ignore #? mypy stupid
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp of validation'
    )
