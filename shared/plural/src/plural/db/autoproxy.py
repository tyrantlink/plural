from datetime import datetime, timedelta
from typing import ClassVar

from beanie import PydanticObjectId
from pydantic import Field

from .base import BaseDocument, ttl
from .enums import AutoProxyMode


class AutoProxy(BaseDocument):
    class Settings:
        name = 'autoproxy'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            ('user', 'guild'),
            ttl()  # ? expire immediately
        ]

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the id of the autoproxy')
    user: PydanticObjectId = Field(
        description='the usergroup id')
    guild: int | None = Field(
        description='the guild id; None if global')
    mode: AutoProxyMode = Field(
        default=AutoProxyMode.LATCH,
        description='the mode of the autoproxy')
    member: PydanticObjectId | None = Field(
        description='the member to proxy to')
    ts: datetime | None = Field(
        description='time when autoproxy will expire; None if never')
