from discord import Interaction, ApplicationContext, Embed, Colour, Message, HTTPException, Forbidden
from discord.ui import Modal as _Modal, InputText, View as _View, Item
from aiohttp import ClientSession, ClientResponse
from discord.utils import _bytes_to_base64_data
from asyncio import sleep, create_task, Task
from hikari import Message as HikariMessage
from collections.abc import Mapping
from src.db import Image, UserProxy
from typing import Iterable, Any
from src.models import project
from functools import partial
from json import dumps, loads
from uuid import uuid4
from io import BytesIO


# ? this is a very unorganized file of anything that might be needed
TOKEN_EPOCH = 1727988244890
BASE66CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789=-_~'
USERPROXY_COMMANDS = [
    {
        'name': 'proxy',
        'type': 1,
        'description': 'send a message',
        'options': [
            {
                'name': 'message',
                'description': 'message to send',
                'max_length': 2000,
                'type': 3,
                'required': False
            },
            {
                'name': 'queue_for_reply',
                'description': 'queue for reply message command (see /help)',
                'type': 5,
                'default': False,
                'required': False
            },
            {
                'name': 'attachment',
                'description': 'attachment to send',
                'type': 11,
                'required': False
            }
        ],
        'integration_types': [1],
        'contexts': [0, 1, 2]
    },
    {
        'name': 'reply',
        'type': 3,
        'integration_types': [1],
        'contexts': [0, 1, 2]
    },
    {
        'name': 'edit',
        'type': 3,
        'integration_types': [1],
        'contexts': [0, 1, 2]
    }
]


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


def create_multipart(
    json_payload: dict,
    files: list[bytes]
) -> tuple[str, bytes]:  # boundary, body
    boundary = uuid4().hex

    body = BytesIO()

    body.write(f'--{boundary}\r\n'.encode('latin-1'))
    body.write(
        f'Content-Disposition: form-data; name="payload_json"\r\n'.encode('latin-1'))
    body.write('Content-Type: application/json\r\n\n'.encode('latin-1'))
    body.write(f'{dumps(json_payload)}\r\n'.encode('latin-1'))

    for index, file in enumerate(files):
        filename = json_payload['data']['attachments'][0]['filename']
        content_type = json_payload['data']['attachments'][0]['content_type']

        body.write(f'--{boundary}\r\n'.encode('latin-1'))
        body.write(
            f'Content-Disposition: form-data; name="files[{index}]"; filename="{filename}"\r\n'.encode('latin-1'))
        body.write(
            f'Content-Type: {content_type}\r\n\n'.encode('latin-1'))
        body.write(file)
        body.write('\r\n'.encode('latin-1'))

    body.write(f'--{boundary}--\r\n'.encode('latin-1'))

    return boundary, body.getvalue()


async def multi_request(
    token: str,
    requests: list[tuple[str, str, dict | None]]
) -> list[tuple[ClientResponse, str]]:
    """requests is a list of tuples of method, endpoint, json"""
    responses: list[tuple[ClientResponse, str]] = []
    async with ClientSession() as session:
        for method, endpoint, json in requests:
            resp = await session.request(
                method,
                f'https://discord.com/api/v10/{endpoint}',
                headers={
                    'Authorization': f'Bot {token}'
                },
                json=json
            )

            if resp.status not in {200, 201}:
                raise HTTPException(resp, await resp.text())

            responses.append((resp, await resp.text()))

    return responses


async def sync_userproxy_with_member(
    ctx: ApplicationContext,
    userproxy: UserProxy,
    bot_token: str,
    sync_commands: bool = False
) -> None:
    assert ctx.interaction.user is not None
    member = await userproxy.get_member()

    image_data = None

    if member.avatar:
        image = await Image.get(member.avatar)
        if image is not None:
            image_data = _bytes_to_base64_data(image.data)

    # ? remember to add user descriptions to userproxy
    bot_patch = {
        'username': member.name,
        'description': f'userproxy for @{ctx.interaction.user.name} powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
    }

    app_patch = {
        'interactions_endpoint_url': f'{project.api_url}/userproxy/interaction'
    }

    # if image_data:
    #     bot_patch['avatar'] = image_data
    #     app_patch['icon'] = image_data

    responses = await multi_request(
        bot_token,
        [
            *(
                [
                    (
                        'post',
                        f'applications/{userproxy.bot_id}/commands',
                        command
                    )
                    for command in USERPROXY_COMMANDS
                ]
                if sync_commands else
                []
            ),
            ('patch', 'users/@me', bot_patch),
            ('get', 'applications/@me', None)
        ]
    )

    for resp, text in responses:
        print(text)

    public_key = (loads(responses[-1][1]))['verify_key']

    userproxy.public_key = public_key

    await userproxy.save()

    app_request = await multi_request(
        bot_token,
        [
            ('patch', f'applications/@me', app_patch)
        ]
    )

    for resp, text in app_request:
        if resp.status != 200:
            print(text)
