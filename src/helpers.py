from discord import Interaction, ApplicationContext, Embed, Colour, Message, HTTPException, Forbidden
from discord.ui import Modal as _Modal, InputText, View as _View, Item
from discord.ext.commands.converter import CONVERTER_MAPPING
from typing import Literal, overload, Iterable, Any
from asyncio import sleep, create_task, Task
from hikari import Message as HikariMessage
from discord.ext.commands import Converter
from collections.abc import Mapping
from beanie import PydanticObjectId
from bson.errors import InvalidId
from src.db import Group, Member
from functools import partial

# ? this is a very unorganized file of anything that might be needed
TOKEN_EPOCH = 1727988244890
BASE66CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=-_~'


class CustomModal(_Modal):
    def __init__(self, title: str, children: list[InputText]) -> None:
        super().__init__(*children, title=title)

    async def callback(self, interaction: Interaction):
        self.interaction = interaction
        self.stop()


class View(_View):
    def __init__(
        self,
        *items: Item,
        timeout: float | None = None,
        disable_on_timeout: bool = False
    ) -> None:
        # ? black magic to stop the view from adding all items on creation and breaking when there's too many
        # ? but still register the attributes as items, mypy is not happy
        tmp, self.__view_children_items__ = self.__view_children_items__, []  # type: ignore
        super().__init__(*items, timeout=timeout, disable_on_timeout=disable_on_timeout)
        self.__view_children_items__ = tmp  # type: ignore

        for func in self.__view_children_items__:
            item: Item = func.__discord_ui_model_type__(  # type: ignore
                **func.__discord_ui_model_kwargs__)  # type: ignore
            item.callback = partial(func, self, item)  # type: ignore
            item._view = self
            setattr(self, func.__name__, item)

    def add_items(self, *items: Item) -> None:
        for item in items:
            if item not in self.children:
                self.add_item(item)


class ErrorEmbed(Embed):
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = 'error'
        self.description = message
        self.colour = Colour(0xff6969)


class SuccessEmbed(Embed):
    def __init__(self, message: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = 'success'
        self.description = message
        self.colour = Colour(0x69ff69)


class ReplyEmbed(Embed):
    # ? this is only here as a fallback if a message is too long for inline reply
    def __init__(self, message: Message | HikariMessage, jump_url: str) -> None:
        super().__init__()

        avatar_url = (
            message.author.display_avatar.url
            if isinstance(message, Message) else
            message.author.display_avatar_url
        )

        self.set_author(
            name=f'{message.author.display_name} ↩️',
            icon_url=avatar_url
        )

        content = (message.content or '').replace('\n', ' ')

        formatted_content = (
            content
            if len(content) <= 75 else
            f'{content[:75].strip()}…'
        )

        self.description = (
            (  # ? i hate this autoformatter sometimes
                f'**[Reply to:]({jump_url})** {formatted_content}')
            if message.content else
            (
                f'*[(click to see attachment{"" if len(message.attachments)-1 else "s"})]({jump_url})*')
            if message.attachments else
            f'*[click to see message]({jump_url})*'
        )


async def send_error(ctx: ApplicationContext | Interaction, message: str) -> None:
    if ctx.response.is_done():
        await ctx.followup.send(
            embed=ErrorEmbed(message),
            ephemeral=True
        )
        return

    await ctx.response.send_message(
        embed=ErrorEmbed(message),
        ephemeral=True
    )


async def send_success(ctx: ApplicationContext | Interaction, message: str) -> None:
    if ctx.response.is_done():
        await ctx.followup.send(
            embed=SuccessEmbed(message),
            ephemeral=True
        )
        return

    await ctx.response.send_message(
        embed=SuccessEmbed(message),
        ephemeral=True
    )


def chunk_string(string: str, chunk_size: int) -> list[str]:
    lines = string.split('\n')

    for i, _ in enumerate(lines):
        if len(lines[i]) > chunk_size:
            raise ValueError(
                f'line {i} is too long ({len(lines[i])}/{chunk_size})')

    chunks = []
    chunk = ''
    for line in lines:
        if len(chunk) + len(line) > chunk_size:
            chunks.append(chunk)
            chunk = ''

        chunk += f'{'\n' if chunk else ''}{line}'

    if chunk:
        chunks.append(chunk)

    return chunks


async def __notify(
    message: Message,
    reaction: str = '❌',
    delay: int | float = 1
) -> None:
    if message._state.user is None:
        return  # ? should never be none but mypy is stupid

    try:
        await message.add_reaction(reaction)
        await sleep(delay)
        await message.remove_reaction(reaction, message._state.user)
    except (HTTPException, Forbidden):
        pass


def notify(
    message: Message,
    reaction: str = '❌',
    delay: int | float = 1
) -> None:
    create_task(__notify(message, reaction, delay))


def format_reply(
    content: str,
    reference: Message | HikariMessage,
    guild_id: int | None = None
) -> str | ReplyEmbed:
    refcontent = (reference.content or '').replace('\n', ' ')
    refattachments = reference.attachments
    mention = (
        reference.author.mention
        if reference.webhook_id is None else
        f'`@{reference.author.display_name}`'
    )
    jump_url = (
        reference.jump_url
        if isinstance(reference, Message) else
        reference.make_link(guild_id)
    )

    base_reply = f'-# [↪](<{jump_url}>) {mention}'

    formatted_refcontent = (
        refcontent
        if len(refcontent) <= 75 else
        f'{refcontent[:75].strip()}…'
    ).replace('://', ':/​/')  # ? add zero-width space to prevent link previews

    reply_content = (
        formatted_refcontent
        if formatted_refcontent else
        f'[*Click to see attachment*](<{jump_url}>)'
        if refattachments else
        f'[*Click to see message*](<{jump_url}>)'
    )

    total_content = f'{base_reply} {reply_content}\n{content}'
    if len(total_content) <= 2000:
        return total_content

    return ReplyEmbed(reference, jump_url)


class DBConversionError(Exception):
    ...


class DBConverter(Converter):
    argument_name = str()

    async def convert(self, ctx: ApplicationContext, value: str):
        match self.argument_name:
            case 'member':
                return await self._handle_member(ctx, value)
            case 'group':
                return await self._handle_group(ctx, value)
            case _:  # ? should never happen
                raise DBConversionError(f'invalid argument `{value}`')

    def _get_options(self, ctx: ApplicationContext) -> dict[str, str]:
        if ctx.interaction.data is None:  # ? should never happen
            raise DBConversionError('interaction data is None')

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


class MemberConverter(DBConverter):
    argument_name = 'member'


class GroupConverter(DBConverter):
    argument_name = 'group'


CONVERTER_MAPPING.update(
    {
        Member: MemberConverter,
        Group: GroupConverter
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


class TTLSet[_T](set):
    def __init__(self, __iterable: Iterable[_T] | None = None, ttl: int = 86400) -> None:
        """a normal set with an async time-to-live (seconds) for each item"""
        __iterable = __iterable or []
        super().__init__(__iterable)
        self.__ttl = ttl
        self._tasks: dict[_T, Task] = {
            __item: create_task(self._expire(__item))
            for __item in
            __iterable
        }

    def _create_expire_task(self, __item: _T) -> None:
        self._tasks[__item] = create_task(self._expire(__item))

    def _cancel_task(self, __item: _T) -> None:
        if __item in self._tasks:
            self._tasks[__item].cancel()
            self._tasks.pop(__item, None)

    async def _expire(self, __item: _T) -> None:
        await sleep(self.__ttl)
        self.discard(__item)

    def add(self, __item: _T) -> None:
        super().add(__item)
        self._cancel_task(__item)
        self._create_expire_task(__item)

    def remove(self, __item: _T) -> None:
        super().remove(__item)
        self._cancel_task(__item)

    def update(self, *s: Iterable[_T]) -> None:
        super().update(*s)

        for iterable in s:
            for __item in iterable:
                self._cancel_task(__item)
                self._create_expire_task(__item)

    def clear(self) -> None:
        super().clear()

        for __item in self:
            self._cancel_task(__item)


class TTLDict[KT, VT](dict):
    def __init__(self, __iterable: Mapping[KT, VT] | None = None, ttl: int = 86400) -> None:
        """a normal dict with an async time-to-live (seconds) for each item"""
        __iterable = __iterable or {}
        super().__init__(__iterable)
        self.__ttl = ttl
        self._tasks: dict[KT, Task] = {
            __key: create_task(self._expire(__key))
            for __key in
            __iterable.keys()
        }

    def _create_expire_task(self, __key: KT) -> None:
        self._tasks[__key] = create_task(self._expire(__key))

    def _cancel_task(self, __key: KT) -> None:
        if __key in self._tasks:
            self._tasks[__key].cancel()
            self._tasks.pop(__key, None)

    async def _expire(self, __key: KT) -> None:
        await sleep(self.__ttl)
        self.pop(__key, None)

    def __setitem__(self, __key: KT, __value: VT) -> None:
        super().__setitem__(__key, __value)
        self._cancel_task(__key)
        self._create_expire_task(__key)

    def __delitem__(self, __key: KT) -> None:
        super().__delitem__(__key)
        self._cancel_task(__key)

    def update(self, __m: Mapping, **kwargs: VT) -> None:
        super().update(__m, **kwargs)

        for __key in __m.keys():
            self._cancel_task(__key)
            self._create_expire_task(__key)

    def clear(self) -> None:
        super().clear()

        for __key in self.keys():
            self._cancel_task(__key)


def encode_b66(b10: int) -> str:
    b66 = ''
    while b10:
        b66 = BASE66CHARS[b10 % 66]+b66
        b10 //= 66
    return b66


def decode_b66(b66: str) -> int:
    b10 = 0
    for i in range(len(b66)):
        b10 += BASE66CHARS.index(b66[i])*(66**(len(b66)-i-1))
    return b10


def merge_dicts(*dicts: Mapping) -> dict:
    """priority is first to last"""
    out: dict[Any, Any] = {}

    for d in reversed(dicts):
        for k, v in d.items():
            if isinstance(v, Mapping):
                out[k] = merge_dicts(out.get(k, {}), v)
            else:
                out[k] = v
    return out
