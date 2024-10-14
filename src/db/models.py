from pydantic import BaseModel, Field, model_validator
from beanie import PydanticObjectId


class ProxyTag(BaseModel):
    prefix: str = Field(
        '',
        max_length=25,
        description='tag must have a prefix or suffix')
    suffix: str = Field(
        '',
        max_length=25,
        description='tag must have a prefix or suffix')
    regex: bool = False

    @model_validator(mode='after')
    def check_prefix_and_suffix(cls, value):
        if not value.prefix and not value.suffix:
            raise ValueError(
                'At least one of prefix or suffix must be non-empty')

        return value


class DatalessImage(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    extension: str
