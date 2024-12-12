from pydantic_core.core_schema import CoreSchema, any_schema
from pydantic.json_schema import JsonSchemaValue
from pydantic import BaseModel
from typing import Self


class RawBaseModel(BaseModel):
    def __init__(self, **data) -> None: # noqa: ANN003
        super().__init__(**data)
        self.__raw_data = data.copy()

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
