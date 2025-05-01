from typing import Self, ClassVar, Any
from enum import Enum

from pydantic_core.core_schema import CoreSchema, any_schema
from pydantic.json_schema import JsonSchemaValue
from pydantic.fields import FieldInfo
from pydantic import BaseModel

from plural.missing import MISSING, _MissingType, is_not_missing
from plural.db import redis


__all__ = (
    'PydanticArbitraryType',
    'RawBaseModel',
)


class RawBaseModel(BaseModel):
    class Config:
        json_encoders: ClassVar[dict[type, type]] = {
            set: list
        }

    def __init__(self, **data) -> None:  # noqa: ANN003
        super().__init__(**data)
        self.__raw_data = data.copy()

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs) -> None:  # noqa: ANN003
        super().__pydantic_init_subclass__(**kwargs)
        for name, field in cls.model_fields.items():
            if (
                (annotation := cls.__annotations__.get(name)) is None or
                not str(annotation).startswith('Optional[')
            ):
                continue

            cls.model_fields[name] = FieldInfo(
                default=MISSING,
                required=False,
                **{
                    k: v
                    for k, v in field._attributes_set.items()
                    if k not in {'default', 'required'}
                }
            )

    @property
    def _raw(self) -> dict:
        return self.__raw_data

    async def populate(self) -> None:
        for field in self.model_fields_set:
            value = getattr(self, field, None)
            if value and issubclass(value.__class__, RawBaseModel):
                await value.populate()

    @classmethod
    async def validate_and_populate(cls, data: dict) -> Self:
        self = cls(**data)

        await self.populate()

        return self

    def as_payload(self) -> dict:
        return filter_missing(self.model_dump())


class DiscordCache(BaseModel):
    data: dict
    meta: dict
    deleted: bool
    error: int

    @property
    def valid(self) -> bool:
        return not self.deleted and not self.error

    @classmethod
    async def fetch(cls, key: str) -> Self | None:
        d: dict[str, Any] = await redis.json().get(f'discord:{key}')

        if d is None:
            return None

        meta = {}

        if d.get('meta', []):
            pipeline = redis.pipeline()

            for k in d['meta']:
                pipeline.smembers(f'discord:{key}:{k}')

            results = await pipeline.execute()

            for key, result in zip(d['meta'], results, strict=True):
                if all(r.isnumeric() for r in result):
                    result = {int(r) for r in result}

                meta[key] = result

        d['meta'] = meta

        return cls(**d)

    async def save(self, key: str) -> None:
        pipeline = redis.pipeline()

        await pipeline.json().set(f'discord:{key}', {
            'data': self.data,
            'meta': list(self.meta.keys()),
            'deleted': self.deleted,
            'error': self.error
        })

        if self.meta:
            for k, v in self.meta.items():
                pipeline.sadd(f'discord:{key}:{k}', *v)

        await pipeline.execute()

    @classmethod
    async def save_invalid(cls, key: str, deleted: bool, error: int) -> None:
        await redis.json().set(f'discord:{key}', {
            'data': {},
            'meta': [],
            'deleted': deleted,
            'error': error
        })


class PydanticArbitraryType:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: None,
        _handler: None
    ) -> CoreSchema:
        return any_schema()

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: None
    ) -> JsonSchemaValue:
        return {'type': 'any'}


def _serialize(value: Any) -> Any:  # noqa: ANN401
    match value:
        case dict():
            return filter_missing(value)
        case list() | set():
            return [
                _serialize(i)
                for i in value]
        case Enum():
            return value.value
        case _MissingType():
            return MISSING

    return value


def filter_missing(data: dict) -> dict:
    filtered = {}

    for k, v in data.items():
        if is_not_missing(value := _serialize(v)):
            filtered[k] = value

    return filtered
