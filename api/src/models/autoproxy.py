from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from beanie import PydanticObjectId


from plural.db import AutoProxy
from plural.db.enums import AutoProxyMode


class AutoProxyPutModel(BaseModel):
    @field_validator('guild', mode='before')
    @classmethod
    def validate_guild(cls, guild: str | int | None) -> str | None:
        return str(guild) if guild is not None else None

    guild: str | None = Field(
        description='The guild id of the autoproxy; None if global')
    mode: AutoProxyMode = Field(
        description='The mode of the autoproxy')
    member: PydanticObjectId | None = Field(
        description='The member to proxy as')
    ts: datetime | None = Field(
        description='Time when autoproxy will expire; None if never')

    def to_autoproxy(
        self,
        usergroup_id: PydanticObjectId
    ) -> AutoProxy:
        return AutoProxy(
            user=usergroup_id,
            guild=self.guild,
            mode=self.mode,
            member=self.member,
            ts=self.ts
        )


class AutoProxyModel(AutoProxyPutModel):
    user: PydanticObjectId = Field(
        description='The usergroup id of the autoproxy')
