from discord.ext.commands.converter import CONVERTER_MAPPING
from src.db import Group, Member, UserProxy
from discord.ext.commands import Converter
from discord import ApplicationContext
from typing import Literal, overload
from beanie import PydanticObjectId
from bson.errors import InvalidId
from enum import Enum


class DBConversionError(Exception):
    ...


class DBConversionType(Enum):
    MEMBER = 1
    GROUP = 2
    USERPROXY = 3


class DBConverter(Converter):
    argument: DBConversionType

    async def convert(self, ctx: ApplicationContext, value: str):
        match self.argument:
            case DBConversionType.MEMBER:
                return await self._handle_member(ctx, value)
            case DBConversionType.GROUP:
                return await self._handle_group(ctx, value)
            case DBConversionType.USERPROXY:
                return await self._handle_userproxy(ctx, value)
            case _:  # ? should never happen
                raise DBConversionError(f'invalid argument `{value}`')

    def _get_options(self, ctx: ApplicationContext) -> dict[str, str]:
        assert ctx.interaction.data is not None

        return {
            # ? type is string, value will always be string
            o['name']: o['value']  # type: ignore
            for o in ctx.interaction.data.get('options', [])
        }

    def _get_reversed_options(self, ctx: ApplicationContext) -> dict[str, str]:
        return {
            v: k
            for k, v in self._get_options(ctx).items()
        }

    @overload
    async def _handle_member(self, ctx: ApplicationContext, value: str) -> Member:
        ...

    @overload
    async def _handle_member(self, ctx: ApplicationContext, value: None) -> None:
        ...

    async def _handle_member(self, ctx: ApplicationContext, value: str | None) -> Member | None:
        if value is None:
            return None

        try:
            parsed_value = PydanticObjectId(value)
        except InvalidId:
            parsed_value = None

        member, group = None, None

        if parsed_value is not None:
            member = await Member.find_one({'_id': parsed_value})

        # ? member argument is not id, try to find by name
        if parsed_value is None and member is None:
            group = await self._handle_group(ctx, self._get_options(ctx).get('group', 'default') or 'default')
            member = await group.get_member_by_name(value)

        if member is None:
            raise DBConversionError('member not found')

        if group is None:
            group = await member.get_group()

        if ctx.author.id not in group.accounts:
            raise DBConversionError('member not found')

        return member

    async def _handle_group(self, ctx: ApplicationContext, value: str | None) -> Group:
        if isinstance(value, str):
            try:
                parsed_value = PydanticObjectId(value)
            except InvalidId:
                parsed_value = None

            group = None

            if parsed_value is not None:
                group = await Group.find_one({'_id': parsed_value})

            # ? group argument is not id, try to find by name
            if parsed_value is None and group is None:
                group = await Group.find_one({'accounts': ctx.author.id, 'name': value})

            if group is None or ctx.author.id not in group.accounts:
                raise DBConversionError('group not found')

            return group

        # ? group argument is None, try to find member argument
        if (member := self._get_options(ctx).get('member', None)) is not None:
            try:
                return await (await self._handle_member(ctx, member)).get_group()
            except DBConversionError:
                # ? no need to actually raise the errors, if member is a supplied argument,
                # ? then those errors will be raised by the member conversion
                pass

        # ? group argument is None and member argument is not found, try to find by default
        group = await Group.find_one({'accounts': ctx.author.id, 'name': 'default'})

        # ? ensure default group always exists
        if group is None:
            group = Group(
                accounts={ctx.author.id},
                name='default',
                avatar=None,
                tag=None
            )
            await group.save()

        return group

    async def _handle_userproxy(self, ctx: ApplicationContext, value: str) -> UserProxy:
        try:
            parsed_value = PydanticObjectId(value)
        except InvalidId:
            parsed_value = None

        userproxy = None

        if parsed_value is not None:
            userproxy = await UserProxy.find_one({'_id': parsed_value})

        if userproxy is None:
            raise DBConversionError('userproxy not found')

        if userproxy.user_id != ctx.author.id:
            raise DBConversionError('userproxy not found')

        return userproxy


class MemberConverter(DBConverter):
    argument = DBConversionType.MEMBER


class GroupConverter(DBConverter):
    argument = DBConversionType.GROUP


class UserProxyConverter(DBConverter):
    argument = DBConversionType.USERPROXY


CONVERTER_MAPPING.update(
    {
        Member: MemberConverter,
        Group: GroupConverter,
        UserProxy: UserProxyConverter
    }
)


def include_all_options(ctx: ApplicationContext) -> Literal[True]:
    if ctx.interaction.data is None:
        return True

    ctx.interaction.data['options'] = [  # type: ignore # ? mypy stupid
        *ctx.interaction.data.get('options', []),
        *[
            {
                'value': o.default,
                'type': o.input_type.value,
                'name': o.name
            }
            for o in ctx.unselected_options or []
        ]
    ]

    return True
