from __future__ import annotations
from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from src.db.models import ProxyTag
from typing import Annotated


class MemberModel(BaseModel):
    name: str = Field(description='the name of the member', max_length=50)
    avatar: PydanticObjectId | None = Field(
        None,
        description='the avatar uuid of the member; overrides the group avatar'
    )
    proxy_tags: Annotated[list[ProxyTag], Field(max_length=5)] = Field(
        [],
        description='proxy tags for the member'
    )


class MemberUpdateModel(BaseModel):
    name: str = Field(
        None, description='the name of the member',  max_length=50)
    avatar: PydanticObjectId | None = Field(
        None,
        description='the avatar uuid of the member; overrides the group avatar'
    )
    proxy_tags: Annotated[list[ProxyTag], Field(max_length=5)] = Field(
        None,
        description='proxy tags for the member'
    )
