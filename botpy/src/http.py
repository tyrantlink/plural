from __future__ import annotations

from inspect import currentframe, getframeinfo
from base64 import b64decode, b64encode
from typing import Any, TYPE_CHECKING
from re import match, IGNORECASE
from urllib.parse import quote
from sys import version_info
from os.path import relpath
from asyncio import sleep

from orjson import loads, dumps
from aiohttp import (
    __version__ as aiohttp_version,
    ServerDisconnectedError,
    ClientResponse,
    ClientSession,
    FormData
)

from plural.otel import inject
from plural.errors import (
    InteractionError,
    HTTPException,
    Forbidden,
    NotFound,
    ServerError,
    Unauthorized
)

from src.version import VERSION

from .models import env

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from io import BufferedIOBase


USER_AGENT = ' '.join([
    f'DiscordBot (https://plural.gg, {VERSION})',
    f'Python/{'.'.join([str(i) for i in version_info])}',
    f'aiohttp/{aiohttp_version}'
])


DISCORD_SESSION = ClientSession()
GENERAL_SESSION = ClientSession()


def get_bot_id_from_token(token: str) -> int:
    m = match(
        r'^(mfa\.[a-z0-9_-]{20,})|(([a-z0-9_-]{23,28})\.[a-z0-9_-]{6,7}\.(?:[a-z0-9_-]{27}|[a-z0-9_-]{38}))$',
        token,
        IGNORECASE
    )

    if m is None:
        raise InteractionError('invalid token format')

    return int(b64decode(f'{m.group(3)}==').decode())


def get_mime_type_for_image(data: bytes) -> str:
    if data.startswith(b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'):
        return 'image/png'
    if data[0:3] == b'\xff\xd8\xff' or data[6:10] in (b'JFIF', b'Exif'):
        return 'image/jpeg'
    if data.startswith((b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61')):
        return 'image/gif'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return 'image/webp'
    raise ValueError('unsupported image type given')


def bytes_to_base64_data(data: bytes) -> str:
    return ''.join([
        'data:', get_mime_type_for_image(data),
        ';base64,', b64encode(data).decode('ascii')
    ])


class Route:
    def __init__(
        self,
        method: str,
        path: str,
        token: str | None = None,
        silent: bool = False,
        **params  # noqa: ANN003
    ) -> None:
        self.method = method
        self.token = token
        self.silent = silent

        if '{application_id}' in path and 'application_id' not in params:
            params['application_id'] = (
                get_bot_id_from_token(token)
                if token is not None and token != env.bot_token
                else env.application_id
            )

        self.path = path.format(**{
            k: quote(v) if isinstance(v, str) else v
            for k, v in params.items()
        }) if params else path

        self.url = f'{env.discord_url}{self.path}'


class File:
    def __init__(
        self,
        data: BufferedIOBase,
        filename: str | None = None,
        description: str | None = None,
        spoiler: bool = False,
        duration_secs: float | None = None,
        waveform: str | None = None,
        size: int | None = None
    ) -> None:
        self.data = data
        self._original_pos = data.tell()
        self.filename = filename
        self.duration_secs = duration_secs
        self.waveform = waveform
        self.size = size

        self._closer = self.data.close
        self.data.close = lambda: None  # type: ignore[method-assign]

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
        self.data.close = self._closer  # type: ignore[method-assign]

    def as_payload(self, index: int) -> dict[str, Any]:
        return {
            'id': index,
            'filename': self.filename,
            'description': self.description,
            'duration_secs': self.duration_secs,
            'waveform': self.waveform,
        }

    def as_form(self, index: int) -> dict[str, Any]:
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


def get_context() -> str:
    frame = currentframe()
    for _ in range(2):
        if frame is None:
            return 'unknown'

        frame = frame.f_back

    info = getframeinfo(frame)

    return f'{relpath(info.filename)}:{info.lineno} {info.function}'.removeprefix('src/')


async def request(
    route: Route,
    files: Sequence[File] | None = None,
    form: Iterable[dict[str, Any]] | None = None,
    json: dict[str, Any] | list[Any] | None = None,
    data: Any | None = None,  # noqa: ANN401
    reason: str | None = None,
    params: dict[str, Any] | None = None,
    **request_kwargs  # noqa: ANN003
) -> dict[str, Any] | str | None:
    headers = {
        'User-Agent': USER_AGENT,
        'X-Context': get_context()
    }

    if route.token is not None:
        headers['Authorization'] = f'Bot {route.token}'

    if route.silent:
        headers['X-Suppress-Tracer'] = '1'

    # ? this is a stupid way of doing this but imma keep it
    if sum((json is not None, data is not None, form is not None)) > 1:
        raise InteractionError('json, data, and form are mutually exclusive')

    if json is not None:
        headers['Content-Type'] = 'application/json'
        data = dumps(json)

    if reason:
        headers['X-Audit-Log-Reason'] = quote(reason, safe='/ ')

    response: ClientResponse | None = None

    for tries in range(5):
        for f in files or []:
            f.reset(seek=tries)

        if form:
            form_data = FormData(quote_fields=False)
            for param in form:
                form_data.add_field(**param)
            data = form_data

        try:
            async with DISCORD_SESSION.request(
                route.method,
                route.url,
                headers=inject(headers),
                data=data,
                params=params,
                **request_kwargs
            ) as response:
                resp_data = await response.text()

                if response.headers.get('Content-Type') == 'application/json':
                    resp_data = loads(resp_data)

                if 300 > response.status >= 200:
                    return resp_data

                if response.status == 429:
                    raise NotImplementedError(
                        'encountered 429 but rate limiting is handled by the egress proxy')

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

        except (OSError, ServerDisconnectedError) as e:
            if isinstance(e, ServerDisconnectedError):
                continue

            if tries < 4 and e.errno in (54, 10054):
                await sleep(1 + tries * 2)
                continue
            raise

    if response is not None:
        if response.status >= 500:
            raise ServerError(data)

        raise HTTPException(data)

    raise RuntimeError('unreachable code in http handling')
