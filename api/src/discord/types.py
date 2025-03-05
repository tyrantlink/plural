from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_core import CoreSchema, core_schema

if TYPE_CHECKING:
    from pydantic.json_schema import JsonSchemaValue
    from pydantic import GetJsonSchemaHandler


__all__ = ('Snowflake',)


class Snowflake(int):
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Snowflake] | None,
        _handler: GetJsonSchemaHandler,
    ) -> CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.int_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {'type': 'string', 'format': 'snowflake'}
