from pydantic import BaseModel, Field
from beanie import PydanticObjectId


class LatchModel(BaseModel):
    user: int = Field(description='user id')
    guild: int = Field(description='guild id')
    enabled: bool = Field(description='whether the latch is enabled')
    member: PydanticObjectId | None = Field(
        description='the latched member id')


class LatchUpdateModel(BaseModel):
    enabled: bool = Field(
        None, description='whether the latch is enabled')
    member: PydanticObjectId = Field(
        None, description='the latched member id')


class LatchCreateModel(BaseModel):
    guild: int = Field(description='guild id')
    enabled: bool = Field(False, description='whether the latch is enabled')
    member: PydanticObjectId = Field(
        None,
        description='the latched member id')
