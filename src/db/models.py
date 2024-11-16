from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from enum import Enum


class DatalessImage(BaseModel):
    id: PydanticObjectId = Field(alias='_id')
    extension: str


class ImageExtension(Enum):
    PNG = 0
    JPG = 1
    GIF = 2
    WEBP = 3
