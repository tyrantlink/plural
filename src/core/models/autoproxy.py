from pydantic import BaseModel, Field
from beanie import PydanticObjectId


class AutoProxyResponse(BaseModel):
    user: int = Field(description='user id')
    guild: int | None = Field(description='guild id, None if global')
    enabled: bool = Field(
        False, description='whether the autoproxy is enabled')
    fronting: bool = Field(
        False, description='whether the autproxy is in fronting mode')
    member: PydanticObjectId | None = Field(
        description='the autoproxied member id')


class AutoProxyPatch(BaseModel):
    enabled: bool | None = Field(
        None, description='whether the autoproxy is enabled')
    fronting: bool | None = Field(
        None, description='whether the autproxy is in fronting mode')
    member: PydanticObjectId | None = Field(
        None, description='the autoproxied member id')


class AutoProxyPost(BaseModel):
    guild: int | None = Field(
        None, description='guild id, None if global')
    enabled: bool = Field(
        False, description='whether the autoproxy is enabled')
    fronting: bool = Field(
        False, description='whether the autproxy is in fronting mode')
    member: PydanticObjectId | None = Field(
        None, description='the autoproxied member id')
