from __future__ import annotations

from aredis_om import Field

from .redis import BaseRedisModel, RedisPK
from .enums import AutoProxyMode


class AutoProxy(BaseRedisModel):
    class Meta:
        model_key_prefix = 'autoproxy'

    user: str = Field(
        index=True,
        description='the user id')
    guild: str | None = Field(
        index=True,
        description='the guild id; None if global')
    mode: AutoProxyMode = Field(
        default=AutoProxyMode.LATCH,
        description='the mode of the autoproxy')
    member: RedisPK = Field(
        description='the member to proxy to')
