from __future__ import annotations
from .helpers import avatar_setter, avatar_deleter, ImageId
from beanie import Document, PydanticObjectId
from pydantic import Field, model_validator
from src.db.member import ProxyMember
from datetime import timedelta
from re import sub, IGNORECASE
from asyncio import gather
from typing import Any


class Group(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @model_validator(mode='before')
    def _list_to_set(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        for variable in {'accounts', 'members', 'channels'}:
            value = values.get(variable, None)
            if value is not None and isinstance(value, list):
                values[variable] = set(value)
        return values

    @model_validator(mode='before')
    def _handle_clyde(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        if (tag := values.get('tag', None)) is None:
            return values

        # ? just stolen from pluralkit https://github.com/PluralKit/PluralKit/blob/214a6d5a4933b975068b0272c98d178a47b487d5/src/pluralkit/bot/proxy.py#L62
        values['tag'] = sub(
            '(c)(lyde)',
            '\\1\u200A\\2',
            tag,
            flags=IGNORECASE
        )
        return values

    @model_validator(mode='before')
    def _handle_avatar(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        if isinstance((avatar := values.get('avatar', None)), bytes):
            values['avatar'] = ImageId.validate(avatar)
        return values

    def dict(self, *args, **kwargs) -> dict[str, Any]:
        data = super().dict(*args, **kwargs)
        for variable in {'accounts', 'members', 'channels'}:
            if data.get(variable, None) is not None:
                data[variable] = list(data[variable])
        return data

    class Settings:
        name = 'groups'
        validate_on_save = True
        use_state_management = True
        cache_expiration_time = timedelta(seconds=2)
        indexes = ['accounts', 'members', 'name']
        bson_encoders = {ImageId: bytes}

    id: PydanticObjectId = Field(  # type: ignore
        default_factory=PydanticObjectId)
    name: str = Field(
        description='the name of the group',
        min_length=1, max_length=45)
    accounts: set[int] = Field(
        default_factory=set,
        description='the discord accounts attached to this group'
    )
    avatar: ImageId | None = Field(
        None,
        description='the avatar uuid of the group'
    )
    channels: set[int] = Field(
        default_factory=set,
        description='the discord channels this group is restricted to'
    )
    tag: str | None = Field(
        None,
        max_length=79,
        description='''
        group tag, displayed at the end of the member name
        for example, if a member has the name 'steve' and the tag is '| the skibidi rizzlers',
        the member's name will be displayed as 'steve | the skibidi rizzlers'
        warning: the total max length of a webhook name is 80 characters
        make sure that the name and tag combined are less than 80 characters
        '''.strip().replace('    ', '')
    )
    members: set[PydanticObjectId] = Field(
        default_factory=set,
        description='the members of the group'
    )

    @property
    def avatar_url(self) -> str | None:
        from src.models import project

        if self.avatar is None:
            return None

        return f'{project.images.base_url}/{self.id}/{self.avatar.id}.{self.avatar.extension}'

    async def get_members(self) -> list[ProxyMember]:
        return await ProxyMember.find_many(
            {'_id': {'$in': list(self.members)}}
        ).to_list()

    async def get_member_by_name(
        self,
        name: str
    ) -> ProxyMember | None:
        return await ProxyMember.find_one(
            {'name': name, '_id': {'$in': list(self.members)}}
        )

    async def add_member(
        self,
        name: str,
        save: bool = True
    ) -> ProxyMember:
        if await self.get_member_by_name(name) is not None:
            raise ValueError(f'member {name} already exists')

        member = ProxyMember(
            name=name,
            avatar=None,
            proxy_tags=[],
            userproxy=None
        )

        self.members.add(member.id)

        if save:
            await gather(
                self.save_changes(),
                member.save()
            )

        return member

    async def delete_member(
        self,
        id: PydanticObjectId
    ) -> None:
        member = await ProxyMember.find_one(
            {'_id': id}
        )

        if member is None:
            raise ValueError(f'member {id} not found')

        if member.id not in self.members:
            raise ValueError(f'member {id} not in group')

        self.members.remove(member.id)

        tasks = [
            self.save_changes(),
            member.delete()
        ]

        if member.avatar is not None:
            tasks.append(member.delete_avatar())

        await gather(*tasks)

    @classmethod
    async def get_or_create_default(cls, account_id: int) -> Group:
        group = await cls.find_one({
            'accounts': account_id,
            'name': 'default'
        })

        if group is not None:
            return group

        return await cls(
            name='default',
            accounts={account_id},
            avatar=None,
            tag=None,
        ).save()

    async def set_avatar(self, url: str) -> None:
        await avatar_setter(self, url)

    async def delete_avatar(self) -> None:
        await avatar_deleter(self)
