from pydantic import BaseModel
from typing import Self

__all__ = ('RawBaseModel',)


class RawBaseModel(BaseModel):
    def __init__(self, **data):
        super().__init__(**data)
        self.__raw_data = data.copy()

    @property
    def _raw(self) -> dict:
        return self.__raw_data

    async def populate(self) -> Self:
        ...

    @classmethod
    async def validate_and_populate(cls, data: dict) -> Self:
        self = cls(**data)

        await self.populate()

        return self
