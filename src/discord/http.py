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
from aiohttp import __version__ as aiohttp_version, FormData, ClientResponse
from asyncio import sleep, Lock, Event, get_event_loop, create_task
from typing import Any, Iterable, Sequence
from datetime import datetime, timezone
from weakref import WeakValueDictionary
from base64 import b64encode, b64decode
from src.core.session import session
from orjson import dumps, loads
from types import TracebackType
from urllib.parse import quote
from src.models import project
from src.db import HTTPCache
from sys import version_info


BASE_URL = 'https://discord.com/api/v10'
USER_AGENT = (
    f'DiscordBot (https://plural.gg, 2.0.0) Python/{'.'.join([str(i) for i in version_info])} aiohttp/{aiohttp_version}')
APPLICATION_ID = int(
    b64decode(project.bot_token.split('.')[0].encode()).decode())

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
        **params
    ) -> None:
        self.method = method
        self.path = path
        url = (BASE_URL if discord else '') + path

        if '{application_id}' in url and 'application_id' not in params:
            params['application_id'] = APPLICATION_ID

        self.url = url.format(**{
            k: quote(v) if isinstance(v, str) else v
            for k, v in params.items()
        }) if params else url

        self.channel_id: int | None = params.get('channel_id')
        self.guild_id: int | None = params.get('guild_id')
        self.webhook_id: int | None = params.get('webhook_id')
        self.webhook_token: str | None = params.get('webhook_token')

    @property
    def bucket(self) -> str:
        return f'{self.channel_id}:{self.guild_id}:{self.path}'


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


class HTTPException(Exception):
    ...


class Forbidden(HTTPException):
    ...


class NotFound(HTTPException):
    ...


class ServerError(HTTPException):
    ...


# ? temp
class File:
    ...

    def reset(self, *, seek: int) -> None:
        ...


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
        raise Exception('unsupported image type given')


def _bytes_to_base64_data(data: bytes) -> str:
    fmt = 'data:{mime};base64,{data}'
    mime = _get_mime_type_for_image(data)
    b64 = b64encode(data).decode('ascii')
    return fmt.format(mime=mime, data=b64)


async def cache_response(route: Route, data: dict | str) -> None:
    if route.method != 'GET' or isinstance(data, str):
        return

    await HTTPCache(
        url=route.url,
        data=data
    ).save()


async def request(
    route: Route,
    *,
    files: Sequence[File] | None = None,
    form: Iterable[dict[str, Any]] | None = None,
    json: dict[str, Any] | None = None,
    data: Any | None = None,
    reason: str | None = None,
    locale: str | None = None,
    **kwargs,
) -> Any:
    if route.method == 'GET':
        cached = await HTTPCache.find_one({'url': route.url})
        if cached is not None:
            return cached.data

    lock = __locks.get(route.bucket)

    if lock is None:
        lock = Lock()
        __locks[route.bucket] = lock

    headers: dict[str, str] = {
        'User-Agent': USER_AGENT,
        'Authorization': f'Bot {project.bot_token}',
    }

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
                            float(request.headers['X-Ratelimit-Reset']),
                            timezone.utc
                        )

                        maybe_lock.defer()
                        loop.call_later(
                            (
                                reset - datetime.now(timezone.utc)
                            ).total_seconds(),
                            lock.release
                        )

                    if 300 > response.status >= 200:
                        create_task(cache_response(route, resp_data))
                        return resp_data

                    if response.status == 429:
                        if not response.headers.get('Via') or isinstance(resp_data, str):
                            raise HTTPException(response, data)

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
                        case 403:
                            raise Forbidden(response, resp_data)
                        case 404:
                            raise NotFound(response, resp_data)
                        case _ if response.status >= 500:
                            raise ServerError(response, resp_data)
                        case _:
                            raise HTTPException(response, resp_data)

            except OSError as e:
                if tries < 4 and e.errno in (54, 10054):
                    await sleep(1 + tries * 2)
                    continue
                raise

        if response is not None:
            if response.status >= 500:
                raise ServerError(response, data)

            raise HTTPException(response, data)

        raise RuntimeError('unreachable code in http handling')


async def get_from_cdn(url: str) -> bytes:
    async with session.get(url) as resp:
        match resp.status:
            case 200:
                return await resp.read()
            case 404:
                raise NotFound(resp, 'asset not found')
            case 403:
                raise Forbidden(resp, 'cannot retrieve asset')
            case _:
                raise HTTPException(resp, 'failed to get asset')
