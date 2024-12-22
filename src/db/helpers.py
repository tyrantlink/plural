from __future__ import annotations
from src.errors import PluralException, ImageLimitExceeded
from pydantic_core import CoreSchema, core_schema
from typing import Any, TYPE_CHECKING
from src.core.session import session
from src.db.config import UserConfig
from .enums import ImageExtension
from src.models import project
from hashlib import md5
import logfire

if TYPE_CHECKING:
    from pydantic import GetJsonSchemaHandler
    from src.db.member import ProxyMember
    from src.db.group import Group


class Image:
    def __init__(self, extension: ImageExtension, hash: str) -> None:
        self.extension = extension
        self.hash = hash

    def __bytes__(self) -> bytes:
        return self.extension.value.to_bytes() + bytes.fromhex(self.hash)

    def __str__(self) -> str:
        return bytes(self).hex()

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Image) and
            self.extension == other.extension and
            self.hash == other.hash
        )

    @property
    def ext(self) -> str:
        return self.extension.name.lower()

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,  # noqa: ANN401
        _handler: GetJsonSchemaHandler,
    ) -> CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.bytes_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(cls),
                core_schema.bytes_schema(),
                core_schema.no_info_plain_validator_function(cls.validate)
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x),
                return_schema=core_schema.str_schema(),
                when_used='json'
            )
        )

    @classmethod
    def validate(cls, value: Any) -> Image:  # noqa: ANN401
        if not isinstance(value, bytes):
            raise ValueError("Invalid value for ImageHash")

        # if len(value) != 17:
        #     raise ValueError("Invalid length for ImageHash bytes")

        return cls(ImageExtension(value[0]), value[1:].hex())


async def _get_image_extension(url: str) -> ImageExtension:
    from src.discord.http import session, _get_mime_type_for_image
    from src.errors import NotFound, Forbidden, HTTPException

    async with session.get(url) as resp:
        match resp.status:
            case 200:
                match _get_mime_type_for_image(await resp.content.read(16)):
                    case 'image/png':
                        return ImageExtension.PNG
                    case 'image/jpeg':
                        return ImageExtension.JPG
                    case 'image/gif':
                        return ImageExtension.GIF
                    case 'image/webp':
                        return ImageExtension.WEBP
                    case _:
                        raise HTTPException('unsupported image type')
            case 404:
                raise NotFound('asset not found')
            case 403:
                raise Forbidden('cannot retrieve asset')
            case _:
                raise HTTPException('failed to get asset')


async def _try_request(method: str, url: str, headers: dict[str, str], data: Any = None, retries=5) -> bool:
    try:
        async with session.request(method, url, headers=headers, data=data) as resp:
            return resp.status == 204
    except Exception as e:
        if retries > 0:
            return await _try_request(method, url, headers, data, retries - 1)
        raise e


async def avatar_deleter(self: ProxyMember | Group, user_id: int, save_and_dec: bool = True) -> None:
    if self.avatar_url is not None:
        if not await _try_request(
            'DELETE',
            self.avatar_url,
            {'Authorization': f'Bearer {project.cdn_api_key}'}
        ):
            logfire.error(f'failed to delete avatar {self.avatar_url}')
            return

    self.avatar = None

    if save_and_dec:
        await UserConfig.dec_images(user_id)
        await self.save()


async def avatar_setter(self: ProxyMember | Group, url: str, user_id: int) -> None:
    config = await UserConfig.get(user_id)

    if config is None:
        config = await UserConfig(id=user_id).save()

    if config.data.images >= config.data.image_limit:
        raise ImageLimitExceeded

    image_response = await session.get(url)

    if int(image_response.headers.get('Content-Length', 0)) > 8_388_608:
        raise PluralException('image must be less than 8MB')

    data = bytearray()

    async for chunk in image_response.content.iter_chunked(8192):
        data.extend(chunk)

        if len(data) > 8_388_608:
            raise PluralException('image must be less than 8MB')

    avatar = Image(await _get_image_extension(url), md5(data).hexdigest())

    if not await _try_request(
        'PUT',
        f'{project.cdn_url}/images/{self.id}/{avatar.hash}.{avatar.ext}',
        {
            'Authorization': f'Bearer {project.cdn_api_key}',
            'Content-Type': avatar.extension.mime_type
        },
        bytes(data)
    ):
        logfire.error(f'failed to upload avatar {avatar.hash}.{avatar.ext}')
        return

    await (
        UserConfig.inc_images(user_id)
        if self.avatar is None else
        avatar_deleter(self, user_id, False)
    )

    self.avatar = avatar
    await self.save()


async def avatar_getter(self: ProxyMember | Group) -> bytes | None:
    if self.avatar_url is None:
        return None

    async with session.get(self.avatar_url) as resp:
        return await resp.read()
