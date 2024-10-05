from beanie import Document, PydanticObjectId
from pydantic import Field, model_validator
from src.db.member import Member
from datetime import timedelta
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

    def dict(self, *args, **kwargs) -> dict[str, Any]:
        data = super().dict(*args, **kwargs)
        for variable in {'accounts', 'members', 'channels'}:
            if data.get(variable, None) is not None:
                data[variable] = list(data[variable])
        self._cache
        return data

    class Settings:
        name = 'groups'
        validate_on_save = True
        use_state_management = True
        indexes = ['accounts', 'members']

    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    name: str = Field(description='the name of the system')
    accounts: set[int] = Field(
        default_factory=set,
        description='the discord accounts attached to this group'
    )
    avatar: PydanticObjectId | None = Field(
        None,
        description='the avatar uuid of the system'
    )
    channels: set[int] = Field(
        default_factory=set,
        description='the discord channels this group is restricted to'
    )
    tag: str | None = Field(
        None,
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

    async def get_members(self) -> list[Member]:
        return await Member.find_many(
            {'_id': {'$in': list(self.members)}}
        ).to_list()

    async def get_member_by_name(
        self,
        name: str
    ) -> Member | None:
        return await Member.find_one(
            {'name': name, '_id': {'$in': list(self.members)}}
        )

    async def add_member(
        self,
        name: str,
        save: bool = True
    ) -> Member:
        if await self.get_member_by_name(name) is not None:
            raise ValueError(f'member {name} already exists')

        member = Member(
            name=name,
            avatar=None,
            proxy_tags=[]
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
        member = await Member.find_one(
            {'_id': id}
        )

        if member is None:
            raise ValueError(f'member {id} not found')

        self.members.remove(member.id)

        await gather(
            self.save_changes(),
            member.delete()
        )
