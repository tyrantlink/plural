from __future__ import annotations

from datetime import timedelta

from aredis_om import Field

from .redis import BaseRedisModel, RedisPK


class Share(BaseRedisModel):
    class Meta:
        model_key_prefix = 'share'
        expire = timedelta(days=1)

    sharer: str = Field(
        index=True,
        description='sharer user id')
    sharee: str = Field(  # ? is optional for some reason in v2
        index=True,
        description='sharee user id')
    group: RedisPK = Field(
        description='group id')
