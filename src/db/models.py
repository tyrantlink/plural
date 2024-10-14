from pydantic import BaseModel, Field, model_validator, ValidationError
from beanie import PydanticObjectId


class ProxyTag(BaseModel):
    prefix: str = Field(
        '',
        max_length=10,
        description='tag must have a prefix or suffix')
    suffix: str = Field(
        '',
        max_length=10,
        description='tag must have a prefix or suffix')
    regex: bool = False

    @model_validator(mode='after')
    def check_prefix_and_suffix(cls, values):
        prefix = values.get('prefix', '')
        suffix = values.get('suffix', '')

        if not prefix and not suffix:
            raise ValidationError(
                'At least one of prefix or suffix must be non-empty')

        return values


class DatalessImage(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    extension: str
