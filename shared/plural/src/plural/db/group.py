from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING, Any
from datetime import timedelta
from re import sub, IGNORECASE

from pydantic import Field, model_validator
from beanie import PydanticObjectId

from plural.env import env

from .enums import GroupSharePermissionLevel  # noqa: TC001
from .member import ProxyMember
from .base import BaseDocument

if TYPE_CHECKING:
    from aiohttp import ClientSession


class Group(BaseDocument):
    class Settings:
        name = 'groups'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            'name',
            'accounts',
            'users',
            'members',
            'avatar'
        ]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @model_validator(mode='before')
    @classmethod
    def _handle_clyde(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        if (tag := values.get('tag')) is None:
            return values

        # ? just stolen from pluralkit https://github.com/PluralKit/PluralKit/blob/214a6d5a4933b975068b0272c98d178a47b487d5/src/pluralkit/bot/proxy.py#L62
        values['tag'] = sub(
            '(c)(lyde)',
            '\\1\u200A\\2',
            tag,
            flags=IGNORECASE
        )
        return values

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the id of the group')
    name: str = Field(
        description='the name of the group',
        min_length=1,
        max_length=45)
    accounts: set[PydanticObjectId] = Field(
        description='the usergroups attached to this group')
    users: dict[int, GroupSharePermissionLevel] = Field(
        default_factory=dict,
        description='the users this group is shared with, and their permission levels')
    avatar: str | None = Field(
        None,
        description='the avatar hash of the group')
    channels: set[int] = Field(
        default_factory=set,
        description='the discord channels this group is restricted to')
    tag: str | None = Field(
        None,
        max_length=79,
        description='the tag of the group')
    members: set[PydanticObjectId] = Field(
        default_factory=set,
        description='the members of the group'
    )

    @property
    def avatar_url(self) -> str | None:
        return env.avatar_url.format(
            parent_id=self.id,
            hash=self.avatar
        ) if self.avatar else None

    @classmethod
    async def default(
        cls,
        usergroup_id: PydanticObjectId,
        user_id: int
    ) -> Group:
        return await Group.find_one({
            'name': 'default',
            '$or': [
                {'accounts': usergroup_id},
                {f'users.{user_id}': {'$exists': True}}]
        }) or Group(
            name='default',
            accounts={usergroup_id}
        )

    async def get_members(
        self,
        limit: int | None = None,
        skip: int | None = None
    ) -> list[ProxyMember]:
        return await ProxyMember.find(
            {'_id': {'$in': list(self.members)}},
            limit=limit,
            skip=skip
        ).to_list()

    async def get_member_by_name(
        self,
        name: str,
        meta: str
    ) -> ProxyMember | None:
        return await ProxyMember.find_one({
            'name': name,
            'meta': meta,
            '_id': {'$in': list(self.members)}
        })

    async def fetch_avatar(
        self,
        session: ClientSession
    ) -> bytes | None:
        if self.avatar is None:
            return None

        async with session.get(self.avatar_url) as response:
            return await response.read()
