from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from plural.db import ProxyMember, Usergroup


class UserProxyModel(BaseModel):
    @field_validator('bot_id', mode='before')
    @classmethod
    def validate_bot_id(cls, bot_id: str | int) -> str:
        return str(bot_id)

    bot_id: str = Field(
        description='Bot id')
    token: str = Field(
        description='The userproxy bot token')
    command: str = Field(
        description='Name of the proxy command'
    )

    @classmethod
    def from_member(
        cls,
        member: ProxyMember
    ) -> Usergroup:
        if member.userproxy is None:
            raise ValueError(
                'Member does not have a userproxy'
            )

        return cls(**member.userproxy.model_dump())
