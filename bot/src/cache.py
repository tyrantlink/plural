from dataclasses import dataclass
from datetime import timedelta
from typing import Self
from time import time

from plural.db import redis


# ? i'm so good at names
_cache_cache: dict[str, tuple[float, dict | None]] = {}


@dataclass
class Cache:
    data: dict
    meta: list[str]
    deleted: bool
    error: int

    @classmethod
    def default(cls) -> Self:
        return cls({}, [], False, 0)

    @classmethod
    async def get(cls, key: str, force_fetch: bool = False) -> Self | None:
        timestamp, data = _cache_cache.get(key, (0, {}))
        if force_fetch or timestamp < time() - 0.200:
            data = await redis.json().get(key)
            _cache_cache[key] = (time(), data)
        return cls(**data) if data is not None else None

    async def fetch_meta(self, key: str, parent: str = 'guild') -> list[Self]:
        pipeline = redis.pipeline()

        for meta_id in await redis.smembers(
            f'discord:{parent}:{self.data["id"]}:{key}'
        ):
            await pipeline.json().get(f'discord:{key.rstrip('s')}:{meta_id}')

        meta_data_list = await pipeline.execute()

        return [
            self.__class__(**data)
            for data in
            meta_data_list
        ]

    async def save(self, key: str, expire: timedelta | None = None) -> Self:
        pipeline = redis.pipeline()
        await pipeline.json().set(key, '$', self.__dict__)

        if expire:
            await pipeline.expire(key, expire)

        await pipeline.execute()

        _cache_cache[key] = (time(), self.__dict__)

        return self
