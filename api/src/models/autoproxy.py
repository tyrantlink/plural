from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from beanie import PydanticObjectId

from plural.db.enums import AutoProxyMode


class AutoProxyModel(BaseModel):
    @field_validator('guild', mode='before')
    @classmethod
    def validate_guild(cls, guild: str | int | None) -> str | None:
        return str(guild) if guild is not None else None

    user: PydanticObjectId = Field(
        description='The usergroup id of the autoproxy')
    guild: str | None = Field(
        description='The guild id of the autoproxy; None if global')
    mode: AutoProxyMode = Field(
        default=AutoProxyMode.LATCH,
        description='The mode of the autoproxy')
    member: PydanticObjectId | None = Field(
        description='The member to proxy as')
    ts: datetime | None = Field(
        description='Time when autoproxy will expire; None if never')
