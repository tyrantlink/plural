from __future__ import annotations

from datetime import timedelta

from aredis_om import Field

from .redis import BaseRedisModel


class Interaction(BaseRedisModel):
    class Meta:
        model_key_prefix = 'interaction'
        expire = timedelta(minutes=14, seconds=45)

    author: str = Field(
        description='the author id')
    bot: str = Field(
        index=True,
        description='the id of the userproxy')
    message: str = Field(
        index=True,
        description='the id of the message')
    channel: str = Field(
        index=True,
        description='the channel id')
    token: str = Field(
        description='the interaction token')
