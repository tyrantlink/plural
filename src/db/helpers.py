from __future__ import annotations
from pydantic_core import CoreSchema, core_schema
from pydantic.json_schema import JsonSchemaValue
from pydantic import GetJsonSchemaHandler
from aiohttp import MultipartWriter
from beanie import PydanticObjectId
from typing import TYPE_CHECKING
from src.models import project
from secrets import token_hex
from typing import Any
from enum import Enum

if TYPE_CHECKING:
    from src.db.member import ProxyMember
    from src.db.group import Group


class ImageExtension(Enum):
    PNG = 0
    JPG = 1
    JPEG = 1
    GIF = 2
    WEBP = 3


class ImageId:
    def __init__(self, extension: ImageExtension, oid: PydanticObjectId | None = None):
        self.extension = extension
        self.id = oid or PydanticObjectId()

    def __bytes__(self) -> bytes:
        return self.extension.value.to_bytes() + self.id.binary

    def __str__(self) -> str:
        return bytes(self).hex()

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
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
    def validate(cls, value: Any) -> ImageId:
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
    from src.discord.http import Route, request

    if self.avatar is not None:
        await request(
            Route(
                'DELETE',
                'https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1/{id}',
                discord=False,
                account_id=project.images.account_id,
                id=f'{self.id}_{self.avatar.id}'),
            token=project.images.token
        )

    self.avatar = None
    await self.save()


async def avatar_setter(self: ProxyMember | Group, url: str) -> None:
    from src.discord.http import Route, request

    avatar = ImageId(await _get_image_extension(url))
    form = {
        'url': url,
        'id': f'{self.id}_{avatar.id}'
    }

    with MultipartWriter('form-data', f'---{token_hex(8)}') as writer:
        for key, value in form.items():
            part = writer.append(value, {'content-type': 'form-data'})
            part.set_content_disposition('form-data', name=key)

        await request(
            Route(
                'POST',
                'https://api.cloudflare.com/client/v4/accounts/{account_id}/images/v1',
                discord=False,
                account_id=project.images.account_id),
            data=writer,
            token=project.images.token
        )

    await avatar_deleter(self)

    self.avatar = avatar
    await self.save()
