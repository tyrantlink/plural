from __future__ import annotations

from typing import Self, TYPE_CHECKING, Annotated
from abc import ABC

from pydantic import StringConstraints
from aredis_om import JsonModel
from bson import ObjectId


if TYPE_CHECKING:
    from redis.client import Pipeline


RedisPK = Annotated[str, StringConstraints(
    strip_whitespace=True,
    to_lower=True,
    pattern=r'^[a-z0-9]+$')]
"""Redis Primary Key"""


class RedisPKCreator:
    B36CHARS = '0123456789abcdefghijklmnopqrstuvwxyz'

    @staticmethod
    def create_pk(*args, oid: ObjectId | None = None, **kwargs) -> str:
        value, result = int.from_bytes((oid or ObjectId()).binary), ''
        while value:
            value, i = divmod(value, 36)
            result = RedisPKCreator.B36CHARS[i] + result

        return result


def stupid_dumb_stupid_redis_om_patch():
    # ? current version of redis om only supports strings in lists and tuples
    # ? but it works just fine without this check and i need to store not strings

    # ? keeping these imports here since i'm going to remove them
    # ? as soon as i don't need to patch the function anymore
    from inspect import getsource
    from textwrap import dedent
    from re import sub

    method = JsonModel.schema_for_type.__func__

    source = dedent(sub(r'\n +'.join([
        '',  # ? empty string to insert \n + at the start
        r'if typ is not str:',
        r'raise RedisModelError\(',
        r'"In this Preview release, list and tuple fields can only "',
        r'f"contain strings. Problem field: {name}. See docs: TODO"',
        r'\)']),
        '',
        getsource(method).split('\n', 1)[1]
    ))

    namespace = {}
    exec(source, method.__globals__, namespace)
    return classmethod(next(iter(namespace.values())))


class BaseRedisModel(JsonModel, ABC):
    schema_for_type = stupid_dumb_stupid_redis_om_patch()

    class Meta:
        primary_key_creator_cls = RedisPKCreator

    @classmethod
    def make_key(cls, part: str):
        return f"{cls._meta.model_key_prefix}:{part}"

    async def save(
        self: Self, pipeline: Pipeline | None = None
    ) -> Self:
        await super().save(pipeline=pipeline)
        if expire := getattr(self._meta, "expire", None):
            await self.expire(expire, pipeline)
