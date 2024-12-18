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
from asyncio import sleep, Lock, Event, get_event_loop, Semaphore
from datetime import datetime, timezone
from weakref import WeakValueDictionary
from base64 import b64encode, b64decode
from typing import Any, TYPE_CHECKING
from src.core.session import session
from dataclasses import dataclass
from re import match, IGNORECASE
from src.version import VERSION
from orjson import dumps, loads
from urllib.parse import quote
from src.models import project
from sys import version_info
from time import time


if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from io import BufferedIOBase


BASE_URL = 'https://discord.com/api/v10'
USER_AGENT = ' '.join([
    f'DiscordBot (https://plural.gg, {VERSION})',
    f'Python/{'.'.join([str(i) for i in version_info])}',
    f'aiohttp/{aiohttp_version}'
])

global_limit = Event()
global_limit.set()
__rate_limits: dict[str, RateLimit] = {}
loop = get_event_loop()


@dataclass
class RateLimit:
    semaphore: Semaphore
    limit: int = 1
    remaining: int = 1
    reset: float = 0.0

    @property
    def is_reset(self) -> bool:
        return self.reset <= time()

    @property
    def reset_after(self) -> float:
        return max(self.reset - time(), 0)


class Route:
    def __init__(
        self,
        method: str,
        path: str,
        discord: bool = True,
        token: str | None = None,
        **params  # noqa: ANN003
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
    ) -> None:
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


def _get_mime_type_for_image(data: bytes) -> str:
    if data.startswith(b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'):
        return 'image/png'
    if data[0:3] == b'\xff\xd8\xff' or data[6:10] in (b'JFIF', b'Exif'):
        return 'image/jpeg'
    if data.startswith((b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61')):
        return 'image/gif'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
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


def update_rate_limit(
    bucket: str,
    limit: int | str | None,
    remaining: int | str | None,
    reset: float | str | None
) -> None:
    rate_limit = __rate_limits.get(bucket, RateLimit(Semaphore(1)))

    if isinstance(limit, str):
        limit = int(limit)

    if isinstance(remaining, str):
        remaining = int(remaining)

    if isinstance(reset, str):
        reset = float(reset)

    if limit is not None and limit != rate_limit.limit:
        rate_limit.limit = limit

        old_sem = rate_limit.semaphore
        rate_limit.semaphore = Semaphore(max(int(limit / 5), 1))

        for _ in range(old_sem._value):
            old_sem.release()

    if remaining is not None:
        rate_limit.remaining = remaining

    if reset is not None:
        rate_limit.reset = reset


async def request(
    route: Route,
    *,
    files: Sequence[File] | None = None,
    form: Iterable[dict[str, Any]] | None = None,
    json: dict[str, Any] | list[Any] | None = None,
    data: Any | None = None,  # noqa: ANN401
    reason: str | None = None,
    locale: str | None = None,
    token: str | None = project.bot_token,
    **kwargs,  # noqa: ANN003
) -> Any:  # noqa: ANN401
    route.token = token

    rate_limit = __rate_limits.get(route.bucket)

    if rate_limit is None:
        rate_limit = RateLimit(Semaphore(1))
        __rate_limits[route.bucket] = rate_limit

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

    if rate_limit.remaining == 0 and not rate_limit.is_reset:
        await sleep(rate_limit.reset_after)

    async with rate_limit.semaphore:
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
                    if route.method == 'HEAD':
                        return response.status == 200

                    update_rate_limit(
                        route.bucket,
                        response.headers.get('X-RateLimit-Limit'),
                        response.headers.get('X-RateLimit-Remaining'),
                        response.headers.get('X-RateLimit-Reset')
                    )

                    resp_data = await json_or_text(response)

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
