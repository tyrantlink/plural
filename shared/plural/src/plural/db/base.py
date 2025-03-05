from collections import OrderedDict
from datetime import timedelta
from typing import Self, Any
from functools import wraps

from beanie.odm.cache import CachedItem
from pymongo import IndexModel
from beanie import Document


def ttl(
    days: float | int = 0,
    hours: float | int = 0,
    minutes: float | int = 0,
    seconds: float | int = 0,
    field: str = 'ts'
) -> IndexModel:
    return IndexModel(
        field,
        expireAfterSeconds=timedelta(
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds
        ).total_seconds()
    )


def invalidate_cache(
    cache: OrderedDict[Any, CachedItem],
    id: Any  # noqa: ANN401
) -> OrderedDict:
    out = OrderedDict()
    for key, cache_item in cache.items():
        match cache_item.value:
            case dict():
                if cache_item.value.get('_id') != id:
                    out[key] = cache_item
            case list():
                if (new_value := [
                    item
                    for item in
                    cache_item.value
                    if item.get('_id') != id
                ]):
                    out[key] = CachedItem(
                        timestamp=cache_item.timestamp,
                        value=new_value
                    )
            case None:
                pass
            case _:
                raise ValueError(
                    f'Invalid cache item type: {type(cache_item.value)}'
                )

    return out


class BaseDocument(Document):
    @wraps(Document.save)
    async def save(
        self,
        *args,  # noqa: ANN002
        **kwargs  # noqa: ANN003
    ) -> Self:
        # ? this is really inefficient, but most cache is only 500ms
        # ? so this shouldn't take that long
        if self._cache:
            self._cache.cache = invalidate_cache(
                self._cache.cache,
                self.id
            )

        return await super().save(*args, **kwargs)
