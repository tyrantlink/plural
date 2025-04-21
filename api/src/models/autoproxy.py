from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from fastapi.exceptions import RequestValidationError
from beanie import PydanticObjectId

from plural.db import Autoproxy, ProxyMember, Usergroup
from plural.db.enums import AutoproxyMode


class AutoproxyPutModel(BaseModel):
    @field_validator('guild', mode='before')
    @classmethod
    def validate_guild(cls, guild: str | int | None) -> str | None:
        return str(guild) if guild is not None else None

    guild: str | None = Field(
        description='The guild id of the autoproxy; null if global')
    mode: AutoproxyMode = Field(
        description='The mode of the autoproxy\n\nModes:\n\n' + '\n\n'.join([
            f'`{mode.value}`: {mode.name.capitalize()}\n\n{mode.description}'
            for mode in AutoproxyMode]))
    member: PydanticObjectId | None = Field(
        description='The member to proxy as')
    ts: datetime | None = Field(
        description='Time when autoproxy will expire; null if never')

    def to_autoproxy(
        self,
        usergroup_id: PydanticObjectId
    ) -> Autoproxy:
        return Autoproxy(
            user=usergroup_id,
            guild=self.guild,
            mode=self.mode,
            member=self.member,
            ts=self.ts
        )


class AutoproxyPatchModel(BaseModel):
    mode: AutoproxyMode = Field(
        default_factory=lambda: AutoproxyMode.LATCH,
        description='The mode of the autoproxy\n\nModes:\n\n' + '\n\n'.join([
            f'`{mode.value}`: {mode.name.capitalize()}\n\n{mode.description}'
            for mode in AutoproxyMode]))
    member: PydanticObjectId | None = Field(
        default_factory=lambda: None,
        description='The member to proxy as')
    ts: datetime | None = Field(
        default_factory=lambda: None,
        description='Time when autoproxy will expire; None if never')

    async def validate_patch(
        self,
        usergroup: Usergroup
    ) -> None:
        for field in self.model_fields_set:
            match field:
                case 'member' if (
                    self.member is not None and (
                        (member := await ProxyMember.get(self.member)) is None or
                        (await member.get_group()).account != usergroup.id
                    )
                ):
                    raise RequestValidationError(
                        errors=[{
                            'loc': ['body', 'member'],
                            'msg': f'Member {self.member} not found',
                            'type': 'value_error'
                        }]
                    )
                case _:
                    pass


class AutoproxyModel(AutoproxyPutModel):
    user: PydanticObjectId = Field(
        description='The usergroup id of the autoproxy')
