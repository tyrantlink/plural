from __future__ import annotations
from pydantic_core import CoreSchema, core_schema
from src.errors import PluralException
from typing import Any, TYPE_CHECKING
from src.core.session import session
from beanie import PydanticObjectId
from .enums import ImageExtension
from src.models import project
import logfire

if TYPE_CHECKING:
    from pydantic import GetJsonSchemaHandler
    from src.db.member import ProxyMember
    from src.db.group import Group


class ImageId:
    def __init__(self, extension: ImageExtension, oid: PydanticObjectId | None = None) -> None:
        self.extension = extension
        self.id = oid or PydanticObjectId()

    def __bytes__(self) -> bytes:
        return self.extension.value.to_bytes() + self.id.binary

    def __str__(self) -> str:
        return bytes(self).hex()

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any, # noqa: ANN401
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
    def validate(cls, value: Any) -> ImageId: # noqa: ANN401
        if not isinstance(value, bytes):
            raise ValueError("Invalid value for ImageId")

        if len(value) != 13:
            raise ValueError("Invalid length for ImageId bytes")

        return cls(ImageExtension(value[0]), PydanticObjectId(value[1:]))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ImageId) and
            self.extension == other.extension and
            self.id == other.id
        )


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


async def avatar_deleter(self: ProxyMember | Group) -> None:
    if self.avatar_url is not None:
        async with session.delete(
            self.avatar_url,
            headers={'Authorization': f'Bearer {project.cdn_api_key}'}
        ) as resp:
            if resp.status != 204:
                logfire.error(
                    'failed to delete avatar {avatar_url} with status {status} and message {message}',
                    avatar_url=self.avatar_url, status=resp.status, message=await resp.text())

    self.avatar = None
    await self.save()


async def avatar_setter(self: ProxyMember | Group, url: str) -> None:
    avatar = ImageId(await _get_image_extension(url))

    image_response = await session.get(url)

    if int(image_response.headers.get('Content-Length', 0)) > 8_388_608:
        raise PluralException('image must be less than 8MB')

    data = bytearray()

    async for chunk in image_response.content.iter_chunked(8192):
        data.extend(chunk)

        if len(data) > 8_388_608:
            raise PluralException('image must be less than 8MB')

    async with session.put(
        f'{project.cdn_url}/images/{self.id}/{avatar.id}.{avatar.extension.name.lower()}',
        data=bytes(data),
        headers={
            'Authorization': f'Bearer {project.cdn_api_key}',
            'Content-Type': avatar.extension.mime_type
        }
    ) as resp:
        if resp.status != 204:
            logfire.error(
                'failed to upload avatar {avatar_id}.{extension} with status {status} and message {message}',
                avatar_id=avatar.id, extension=avatar.extension, status=resp.status, message=await resp.text())
            return None

    await avatar_deleter(self)

    self.avatar = avatar
    await self.save()


async def avatar_getter(self: ProxyMember | Group) -> bytes | None:
    if self.avatar_url is None:
        return None

    async with session.get(self.avatar_url) as resp:
        return await resp.read()
