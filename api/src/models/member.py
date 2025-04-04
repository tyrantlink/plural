from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator
from beanie import PydanticObjectId

from plural.db.enums import ApplicationScope


if TYPE_CHECKING:
    from plural.db import ProxyMember, Usergroup

    from src.core.auth import TokenData


class MemberModel(BaseModel):
    class ProxyTag(BaseModel):
        id: PydanticObjectId = Field(
            default_factory=PydanticObjectId,
            description='The id of the proxy tag')
        prefix: str = Field(
            '',
            max_length=50,
            description='The tag prefix; {prefix}text{suffix}')
        suffix: str = Field(
            '',
            max_length=50,
            description='The tag suffix; {prefix}text{suffix}')
        regex: bool = Field(
            False)
        case_sensitive: bool = Field(
            False)
        avatar: str | None = Field(
            None,
            description='The avatar hash of this proxy tag'
        )

    class UserProxy(BaseModel):
        @field_validator('bot_id', mode='before')
        @classmethod
        def validate_bot_id(cls, bot_id: str | int) -> str:
            return str(bot_id)

        @field_validator('guilds', mode='before')
        @classmethod
        def validate_guilds(cls, guilds: set[str | int]) -> set[str]:
            return {str(guild_id) for guild_id in guilds}

        bot_id: str = Field(
            description='Bot id')
        public_key: str = Field(
            description='The userproxy public key')
        token: str = Field(
            description='The userproxy bot token')
        command: str = Field(
            'proxy',
            description='Name of the proxy command')
        guilds: set[str] = Field(
            default_factory=set,
            description='The guilds the userproxy is enabled in'
        )

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='The id of the member')
    name: str = Field(
        description='The name of the member',
        min_length=1,
        max_length=80)
    meta: str = Field(
        '',
        description='The meta information of the member; only shown in autocomplete',
        max_length=50)
    pronouns: str = Field(
        '',
        description='The pronouns of the member')
    bio: str = Field(
        '',
        description='The bio of the member',
        max_length=4000)
    birthday: str = Field(
        '',
        description='The birthday of the member')
    color: int | None = Field(
        None,
        description='The color of the member')
    avatar: str | None = Field(
        None,
        description='The avatar hash of the member')
    proxy_tags: list[ProxyTag] = Field(
        default_factory=list,
        description='The tags of the member',
        max_length=15)
    userproxy: UserProxy | None = Field(
        None,
        description='The userproxy of the member')
    simplyplural_id: str | None = Field(
        None,
        description='The simplyplural id of the member'
    )

    @classmethod
    def from_member(
        cls,
        usergroup: Usergroup,
        member: ProxyMember,
        token: TokenData
    ) -> Usergroup:
        data = cls(**member.model_dump())

        if token.internal:
            return data

        if member.userproxy is not None and not (
            usergroup.data.applications.get(
                str(token.app_id), ApplicationScope.NONE
            ).value &
            ApplicationScope.USERPROXY_TOKENS.value
        ):
            data.userproxy.public_key = ''
            data.userproxy.token = ''

        if not (
            usergroup.data.applications.get(
                str(token.app_id), ApplicationScope.NONE
            ).value &
            ApplicationScope.SP_TOKENS.value
        ):
            data.simplyplural_id = None

        return data


class UserproxySync(BaseModel):
    author_id: int
    patch_filter: set[str]
