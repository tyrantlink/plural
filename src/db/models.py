from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class ProxyTag(BaseModel):
    prefix: str
    suffix: str
    regex: bool


class DatalessImage(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    extension: str
