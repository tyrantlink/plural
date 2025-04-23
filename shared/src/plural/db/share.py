from datetime import datetime, timedelta
from typing import ClassVar

from beanie import PydanticObjectId
from pydantic import Field

from .enums import ShareType, GroupSharePermissionLevel
from .base import BaseDocument, ttl


class Share(BaseDocument):
    class Settings:
        name = 'shares'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            ('sharer', 'sharee'),  # ? compound index
            ttl(hours=6)
        ]

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId)
    type: ShareType = Field(
        description='type of share')
    sharer: int = Field(
        description='sharer user id')
    sharee: int = Field(
        description='sharee user id')
    group: PydanticObjectId | None = Field(
        description='group id')
    permission_level: GroupSharePermissionLevel | None = Field(
        description='permission level for the sharee; None if not a group share')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp'
    )
