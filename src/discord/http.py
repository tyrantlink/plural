# The MIT License (MIT)

# Copyright (c) 2015-2021 Rapptz
# Copyright (c) 2021-present Pycord Development

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
# ? i stole most of the http stuff from py-cord
from __future__ import annotations
from src.errors import HTTPException, Forbidden, NotFound, ServerError, Unauthorized, InteractionError
from aiohttp import __version__ as aiohttp_version, FormData, ClientResponse
from asyncio import sleep, Lock, Event, get_event_loop, create_task
from typing import Any, Iterable, Sequence
from datetime import datetime, timezone
from weakref import WeakValueDictionary
from base64 import b64encode, b64decode
from src.db.httpcache import HTTPCache
from src.core.session import session
from re import match, IGNORECASE
from src.version import VERSION
from orjson import dumps, loads
from types import TracebackType
from urllib.parse import quote
from src.models import project
from io import BufferedIOBase
from sys import version_info


BASE_URL = 'https://discord.com/api/v10'
USER_AGENT = ' '.join([
    f'DiscordBot (https://plural.gg, {VERSION})',
    f'Python/{'.'.join([str(i) for i in version_info])}',
    f'aiohttp/{aiohttp_version}'
])

global_limit = Event()
global_limit.set()
__locks = WeakValueDictionary()
loop = get_event_loop()


class Route:
    def __init__(
        self,
        method: str,
        path: str,
        discord: bool = True,
        token: str | None = None,
        **params
    ) -> None:
        self.method = method
        self.path = path
        self.token = token
        self.discord = discord
        url = (BASE_URL if discord else '') + path

        if '{application_id}' in url and 'application_id' not in params:
            params['application_id'] = (
                _get_bot_id(token)
                if discord and token is not None and token != project.bot_token
                else project.application_id
            )

        self.url = url.format(**{
            k: quote(v) if isinstance(v, str) else v
            for k, v in params.items()
        }) if params else url

        self.channel_id: int | None = params.get('channel_id')
        self.guild_id: int | None = params.get('guild_id')
        self.webhook_id: int | None = (
            params.get('webhook_id') or
            params.get('interaction_id')
        )
        self.webhook_token: str | None = (
            params.get('webhook_token') or
            params.get('interaction_token')
        )

    @property
    def bucket(self) -> str:
        if self.webhook_id and self.webhook_token:
            return f'{self.webhook_id}:{self.webhook_token}:{self.path}:{self.token}'

        return f'{self.channel_id}:{self.guild_id}:{self.path}:{self.token}'


class MaybeUnlock:
    def __init__(self, lock: Lock) -> None:
        self.lock = lock
        self._unlock = True

    def __enter__(self) -> MaybeUnlock:
        return self

    def defer(self) -> None:
        self._unlock = False

    def __exit__(
        self,
        exc_type: type[Exception] | None,
        exc: Exception | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._unlock:
            self.lock.release()


async def json_or_text(response: ClientResponse) -> dict[str, Any] | str:
    text = await response.text(encoding='utf-8')
    try:
        if response.headers['content-type'] == 'application/json':
            return loads(text)
    except KeyError:
        pass

    return text


class File:
    def __init__(
        self,
        data: BufferedIOBase,
        filename: str | None = None,
        description: str | None = None,
        spoiler: bool = False,
        duration_secs: float | None = None,
        waveform: str | None = None,
    ):
        self.data = data
        self._original_pos = data.tell()
        self.filename = filename
        self.duration_secs = duration_secs
        self.waveform = waveform

        self._closer = self.data.close
        self.data.close = lambda: None

        if (
            spoiler
            and self.filename is not None
            and not self.filename.startswith('SPOILER_')
        ):
            self.filename = f'SPOILER_{self.filename}'

        self.spoiler = spoiler or (
            self.filename is not None and self.filename.startswith('SPOILER_')
        )
        self.description = description

    @property
    def is_voice_message(self) -> bool:
        return self.duration_secs is not None and self.waveform is not None

    def reset(self, *, seek: int | bool = True) -> None:
        if seek:
            self.data.seek(self._original_pos)

    def close(self) -> None:
        self.data.close = self._closer

    def as_payload_dict(self, index: int) -> dict[str, Any]:
        return {
            'id': index,
            'filename': self.filename,
            'description': self.description,
            'duration_secs': self.duration_secs,
            'waveform': self.waveform,
        }

    def as_form_dict(self, index: int) -> dict[str, Any]:
        return {
            'name': f'files[{index}]',
            'value': self.data,
            'filename': self.filename,
            'content_type': (
                'audio/ogg'
                if self.is_voice_message else
                'application/octet-stream'
            ),
        }


def _get_mime_type_for_image(data: bytes):
    if data.startswith(b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'):
        return 'image/png'
    elif data[0:3] == b'\xff\xd8\xff' or data[6:10] in (b'JFIF', b'Exif'):
        return 'image/jpeg'
    elif data.startswith((b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61')):
        return 'image/gif'
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
    else:
        raise ValueError('unsupported image type given')


def _bytes_to_base64_data(data: bytes) -> str:
    return ''.join([
        'data:', _get_mime_type_for_image(data),
        ';base64,', b64encode(data).decode('ascii')
    ])


def _get_bot_id(token: str) -> int:
    m = match(
        r'^(mfa\.[a-z0-9_-]{20,})|(([a-z0-9_-]{23,28})\.[a-z0-9_-]{6,7}\.(?:[a-z0-9_-]{27}|[a-z0-9_-]{38}))$',
        token,
        IGNORECASE
    )

    if m is None:
        raise InteractionError('invalid token format')

    return int(b64decode(f'{m.group(3)}==').decode())


async def cache_response(route: Route, status: int, data: dict | str) -> None:
    if any((
        route.method != 'GET',
        route.token != project.bot_token,
        isinstance(data, str),
        not route.discord
    )):
        return

    await HTTPCache(
        id=route.url,
        status=status,
        data=data
    ).save()


async def request(
    route: Route,
    *,
    files: Sequence[File] | None = None,
    form: Iterable[dict[str, Any]] | None = None,
    json: dict[str, Any] | list[Any] | None = None,
    data: Any | None = None,
    reason: str | None = None,
    locale: str | None = None,
    token: str | None = project.bot_token,
    ignore_cache: bool = False,
    **kwargs,
) -> Any:
    route.token = token

    if (
        not ignore_cache and
        token == project.bot_token and
        route.method == 'GET'
    ):
        cached = await HTTPCache.get(route.url)
        if cached is not None:
            match cached.status:
                case 401:
                    raise Unauthorized(cached.data)
                case 403:
                    raise Forbidden(cached.data)
                case 404:
                    raise NotFound(cached.data)
                case _:
                    return cached.data

    lock = __locks.get(route.bucket)

    if lock is None:
        lock = Lock()
        __locks[route.bucket] = lock

    headers: dict[str, str] = {
        'User-Agent': USER_AGENT
    }

    if token:
        headers['Authorization'] = (
            f'Bot {token}'
            if route.discord
            else f'Bearer {token}'
        )

    if json is not None and data is not None:
        raise TypeError('You can only pass either json or data')

    if json is not None:
        headers['Content-Type'] = 'application/json'
        data = dumps(json)

    if reason:
        headers['X-Audit-Log-Reason'] = quote(reason, safe='/ ')

    if locale:
        headers['X-Discord-Locale'] = locale

    if global_limit.is_set():
        await global_limit.wait()

    response: ClientResponse | None = None
    resp_data: dict[str, Any] | str | None = None
    await lock.acquire()
    with MaybeUnlock(lock) as maybe_lock:
        for tries in range(5):
            if files:
                for f in files:
                    f.reset(seek=tries)

            if form:
                form_data = FormData(quote_fields=False)
                for params in form:
                    form_data.add_field(**params)
                data = form_data

            try:
                async with session.request(
                    route.method,
                    route.url,
                    data=data,
                    headers=headers,
                    **kwargs,
                ) as response:
                    resp_data = await json_or_text(response)

                    if (
                        response.headers.get('X-Ratelimit-Remaining') == '0' and
                        response.status != 429
                    ):
                        reset = datetime.fromtimestamp(
                            float(response.headers.get(
                                'X-Ratelimit-Reset') or 0),
                            timezone.utc
                        )

                        maybe_lock.defer()
                        loop.call_later(
                            (
                                reset - datetime.now(timezone.utc)
                            ).total_seconds(),
                            lock.release
                        )

                    if response.status < 500 and response.status != 429:
                        create_task(cache_response(
                            route, response.status, resp_data))

                    if 300 > response.status >= 200:
                        return resp_data

                    if response.status == 429:
                        if not response.headers.get('Via') or isinstance(resp_data, str):
                            raise HTTPException(data)

                        retry_after: float = resp_data['retry_after']

                        is_global = resp_data.get('global', False)
                        if is_global:
                            global_limit.set()

                        await sleep(retry_after)

                        if is_global:
                            global_limit.clear()

                        continue

                    if response.status in {500, 502, 503, 504}:
                        await sleep(1 + tries * 2)
                        continue

                    match response.status:
                        case 401:
                            raise Unauthorized(resp_data)
                        case 403:
                            raise Forbidden(resp_data)
                        case 404:
                            raise NotFound(resp_data)
                        case _ if response.status >= 500:
                            raise ServerError(resp_data)
                        case _:
                            raise HTTPException(resp_data)

            except OSError as e:
                if tries < 4 and e.errno in (54, 10054):
                    await sleep(1 + tries * 2)
                    continue
                raise

        if response is not None:
            if response.status >= 500:
                raise ServerError(data)

            raise HTTPException(data)

        raise RuntimeError('unreachable code in http handling')


async def get_from_cdn(url: str) -> bytes:
    async with session.get(url) as resp:
        match resp.status:
            case 200:
                return await resp.read()
            case 404:
                raise NotFound('asset not found')
            case 403:
                raise Forbidden('cannot retrieve asset')
            case _:
                raise HTTPException('failed to get asset')
