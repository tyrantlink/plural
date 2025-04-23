from __future__ import annotations

from typing import Any, Literal, TypeGuard, TYPE_CHECKING

from pydantic_core import CoreSchema, core_schema

if TYPE_CHECKING:
    from pydantic import GetJsonSchemaHandler, GetCoreSchemaHandler
    from pydantic.json_schema import JsonSchemaValue


__all__ = (
    'INSTANCE',
    'MISSING',
    'Nullable',
    'Optional',
    '_MissingType',
)


class _MissingType:
    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "MISSING"

    def __copy__(self) -> _MissingType:
        return self

    def __deepcopy__(
        self,
        _: Any  # noqa: ANN401
    ) -> _MissingType:
        return self

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,  # noqa: ANN401
        _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.none_schema(),
            python_schema=core_schema.is_instance_schema(cls),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "null"}


def is_not_missing[T](value: T | _MissingType) -> TypeGuard[T]:
    return not isinstance(value, _MissingType)


MISSING = _MissingType()

INSTANCE = hex(id(MISSING))[2:]

type Optional[T] = T | _MissingType
type Nullable[T] = T | None
