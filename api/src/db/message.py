from __future__ import annotations

from datetime import timedelta

from aredis_om import Field

from .redis import BaseRedisModel
from .enums import ProxyReason


class Message(BaseRedisModel):
    class Meta:
        model_key_prefix = 'message'
        expire = timedelta(days=7)

    original: str | None = Field(
        index=True,
        description='the original message id; None if message sent through api or is userproxy message')
    proxy: str = Field(
        index=True,
        description='the proxy id of the message')
    author: str = Field(
        # index=True, # ! make sure this is needed
        description='the author id of the message')
    channel: str = Field(
        description='the channel id of the message')
    reason: ProxyReason | str = Field(  # ? may be stored as string when reason includes proxy tags
        default=ProxyReason.NONE,
        description='the reason the message was proxied')
