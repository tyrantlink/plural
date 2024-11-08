from pydantic import BaseModel

__all__ = ('RawBaseModel',)


class RawBaseModel(BaseModel):
    def __init__(self, **data):
        super().__init__(**data)
        self.__raw_data = data.copy()

    @property
    def _raw(self) -> dict:
        return self.__raw_data
