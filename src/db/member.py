from beanie import Document, PydanticObjectId
from datetime import timedelta
from .models import ProxyTag
from typing import Annotated
from pydantic import Field


class Member(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'members'
        validate_on_save = True
        use_state_management = True

    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    name: str = Field(description='the name of the member')
    avatar: PydanticObjectId | None = Field(
        None,
        description='the avatar uuid of the member; overrides the group avatar'
    )
    proxy_tags: Annotated[list[ProxyTag], Field(max_length=5)] = Field(
        [],
        description='proxy tags for the member'
    )
