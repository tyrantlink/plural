from typing import ClassVar, Literal

from beanie import PydanticObjectId
from pydantic import Field

from .base import BaseDocument


class Migration(BaseDocument):
    class Settings:
        name = 'migrations'
        validate_on_save = True
        indexes: ClassVar = [
            'user',
            'phase'
        ]

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the id of the migration')
    user: int = Field(description='the user id')
    phase: Literal[0, 1] = Field(
        description='0: needs to pick groups, 1: needs to assign userproxy tokens')
    data: list[dict] = Field(description='the data of the migration')
    index: int = Field(0, description='the index of the migration')
    members: dict[PydanticObjectId, dict] = Field(
        default_factory=dict,
        description='the members of the migration (if phase 0)')
