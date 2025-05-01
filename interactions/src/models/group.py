from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from beanie import PydanticObjectId  # noqa: TC002

from plural.db.enums import GroupSharePermissionLevel  # noqa: TC002
from plural.db import Group  # noqa: TC002


class GroupModel(BaseModel):
    @field_validator('users', mode='before')
    @classmethod
    def validate_users(
        cls,
        users: dict[str | int, GroupSharePermissionLevel]
    ) -> dict[str, GroupSharePermissionLevel]:
        return {
            str(user_id): permission_level
            for user_id, permission_level in
            users.items()
        }

    @field_validator('channels', mode='before')
    @classmethod
    def validate_channels(
        cls,
        channels: set[str | int]
    ) -> set[str]:
        return {str(channel_id) for channel_id in channels}

    id: PydanticObjectId = Field(
        description='The id of the group')
    name: str = Field(
        description='The name of the group',
        min_length=1,
        max_length=45)
    account: PydanticObjectId = Field(
        description='The usergroup attached to this group')
    users: dict[str, GroupSharePermissionLevel] = Field(
        description='The users this group is shared with, and their permission levels')
    avatar: str | None = Field(
        description='The avatar hash of the group')
    channels: set[str] = Field(
        description='The Discord channels this group is restricted to')
    tag: str | None = Field(
        max_length=79,
        description='The tag of the group')
    members: set[PydanticObjectId] = Field(
        description='The members of the group'
    )

    @classmethod
    def from_group(
        cls,
        group: Group
    ) -> GroupModel:
        return cls(**group.model_dump(mode='json'))
