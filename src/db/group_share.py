from beanie import Document, PydanticObjectId
from pymongo import IndexModel
from datetime import datetime
from typing import ClassVar
from pydantic import Field


class GroupShare(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'group_shares'
        validate_on_save = True
        use_state_management = True
        indexes: ClassVar = [
            ('sharer', 'sharee'),  # ? compound index
            IndexModel('ts', expireAfterSeconds=60*60*24)
        ]

    id: PydanticObjectId = Field( # pyright: ignore[reportIncompatibleVariableOverride]
        default_factory=PydanticObjectId)
    sharer: int = Field(description='sharer user id')
    sharee: int | None = Field(description='sharee user id')
    group: PydanticObjectId = Field(description='group id')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp')
