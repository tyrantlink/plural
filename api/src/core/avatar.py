from asyncio import to_thread, sleep
from dataclasses import dataclass
from random import random
from hashlib import md5

from aiohttp import ClientSession, ClientResponse
from pyvips import Image, Error as VipsError

from plural.db import redis, Group, ProxyMember
from plural.errors import PluralException
from plural.otel import span

from .http import GENERAL_SESSION
from .models import env


@dataclass
class Avatar:
    url: str
    size: int
    hash: str
    webp: bool
    data: bytes


async def _response_check(
    url: str,
    response: ClientResponse,
    bypass_limit: bool = False
) -> None:
    if response.status != 200:
        raise PluralException(
            f'failed to download avatar: {url} with reason {await response.text()}'
        )

    if response.content_length is None:
        raise PluralException(f'avatar {url} has no content length')

    if not bypass_limit and int(response.content_length) > env.max_avatar_size:
        raise PluralException(f'avatar {url} too large')

    if response.content_type not in {
        'image/png',
        'image/jpeg',
        'image/gif',
        'image/webp'
    }:
        raise PluralException(
            f'avatar {url} not an image; must be png, jpg, gif, or webp'
        )


async def _download_avatar(
    url: str,
    session: ClientSession,
    bypass_limit: bool = False
) -> Avatar:
    async with session.head(url) as response:
        await _response_check(url, response, bypass_limit)

    async with session.get(url) as response:
        await _response_check(url, response, bypass_limit)

        data = bytearray()

        async for chunk in response.content.iter_chunked(16384):
            data.extend(chunk)

            if not bypass_limit and len(data) > env.max_avatar_size:
                raise PluralException(f'avatar {url} too large')

        image_hash = md5(data).hexdigest()

    return Avatar(
        url=url,
        size=len(data),
        hash=image_hash,
        webp=data.startswith(b'RIFF') and data[8:12] == b'WEBP',
        data=bytes(data)
    )


def _convert_avatar(
    avatar: Avatar
) -> Avatar:
    try:
        image: Image = Image.new_from_buffer(
            avatar.data,
            '',
            n=-1,
            access='sequential')
    except VipsError:
        image: Image = Image.new_from_buffer(
            avatar.data,
            '',
            access='sequential'
        )

    scale = min(
        1024 / image.width,
        1024 / (image.height / image.get_n_pages())
    )

    if scale < 1:
        image = image.resize(scale)

    image_data: bytes = image.write_to_buffer(
        '.webp',
        strip=True,
        Q=80,
        lossless=False,
        target_size=256_000,
        passes=3,
        smart_deblock=True
    )

    if len(image_data) > avatar.size and avatar.webp:
        # ? if the converted image is larger than the original and already webp, keep the original
        return avatar

    return Avatar(
        url=avatar.url,
        size=len(image_data),
        hash=md5(image_data).hexdigest(),
        webp=True,
        data=image_data
    )


async def _upload_avatar(
    parent_id: str,
    session: ClientSession,
    avatar: Avatar,
    tries: int = 0
) -> str:
    if await redis.scard(f'avatar:{avatar.hash}'):
        await redis.sadd(f'avatar:{avatar.hash}', parent_id)
        return avatar.hash

    async with session.put(
        env.avatar_url.format(parent_id=parent_id, hash=avatar.hash),
        data=avatar.data,
        headers={
            'Authorization': f'Bearer {env.cdn_upload_token}',
            'Content-Type': 'image/webp',
            'Content-Length': str(avatar.size)}
    ) as response:
        if response.status // 100 == 5:
            if tries >= 5:
                raise PluralException(
                    f'failed to upload avatar after 5 tries: {await response.text()}'
                )

            await sleep(min(1, random()*5))

            return await _upload_avatar(
                parent_id,
                session,
                avatar,
                tries + 1
            )

        if response.status != 204:
            raise PluralException(
                f'failed to upload avatar: {await response.text()}'
            )

    return avatar.hash


async def upload_avatar(
    parent_id: str,
    url: str,
    session: ClientSession,
    bypass_limit: bool = False
) -> str:
    """returns avatar hash"""
    return await _upload_avatar(
        parent_id,
        session,
        await to_thread(
            _convert_avatar,
            await _download_avatar(
                url,
                session,
                bypass_limit
            )
        )
    )


async def delete_avatar(
    parent_id: str,
    hash: str,
    session: ClientSession,
    tries: int = 0
) -> None:
    if await redis.scard(f'avatar:{hash}') - 1:
        await redis.srem(f'avatar:{hash}', parent_id)
        return None

    async with session.delete(
        env.avatar_url.format(parent_id=parent_id, hash=hash),
        headers={'Authorization': f'Bearer {env.cdn_upload_token}'}
    ) as response:
        if response.status // 100 == 5:
            if tries >= 5:
                raise PluralException(
                    f'failed to delete avatar after 5 tries: {await response.text()}'
                )

            await sleep(min(1, random()*5))

            return await delete_avatar(
                parent_id,
                hash,
                session,
                tries + 1
            )

        if response.status != 204:
            raise PluralException(
                f'failed to delete avatar: {await response.text()}'
            )

    return None


def _convert_for_userproxy(
    original_data: bytes
) -> tuple[str, bytes]:
    try:
        image: Image = Image.new_from_buffer(
            original_data,
            '',
            n=-1,
            access='sequential')
    except VipsError as e:
        raise PluralException(
            'failed to convert avatar for userproxy'
        ) from e

    return (
        'image/png' if image.get_n_pages() == 1 else 'image/gif',
        image.write_to_buffer(
            '.png' if image.get_n_pages() == 1 else '.gif',
            strip=True
        )
    )


async def convert_for_userproxy(
    parent: Group | ProxyMember
) -> tuple[str | None, bytes | None]:
    original_data = await parent.fetch_avatar(GENERAL_SESSION)

    if original_data is None:
        return None, None

    with span('converting avatar for userproxy'):
        return await to_thread(
            _convert_for_userproxy,
            original_data
        )
