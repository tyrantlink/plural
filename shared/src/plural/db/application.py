from typing import ClassVar, Self
from datetime import timedelta
from secrets import token_hex
from hashlib import sha256
from time import time

from beanie import PydanticObjectId
from bcrypt import hashpw, gensalt
from pydantic import Field

from plural.crypto import encode_b66, TOKEN_EPOCH

from .enums import ApplicationScope
from .base import BaseDocument


class Application(BaseDocument):
    class Settings:
        name = 'applications'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            'developer'
        ]

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the id of the application')
    name: str = Field(
        description='the name of the application')
    description: str = Field(
        description='the description of the application')
    icon: str | None = Field(
        description='the icon hash of the application')
    developer: int = Field(
        description='the user id of the developer')
    token: str = Field(
        description='the api key of the application')
    scope: ApplicationScope = Field(
        description='the scope of the application')
    endpoint: str = Field(
        default='',
        description='the endpoint of the application')
    authorized_count: int = Field(
        default=0,
        description='the number of users who have authorized the application'
    )

    @classmethod
    def new(
        cls,
        name: str,
        description: str,
        developer: int,
        scope: ApplicationScope
    ) -> tuple[Self, str]:
        id = PydanticObjectId()

        token = '.'.join([
            encode_b66(int.from_bytes(id.binary)),
            encode_b66(int((time()*1000)-TOKEN_EPOCH)),
            encode_b66(int(token_hex(20), 16))
        ])

        return (
            cls(
                id=id,
                name=name,
                description=description,
                icon=None,
                developer=developer,
                token=hashpw(token.encode(), gensalt()).decode(),
                scope=scope),
            token
        )

    async def update_token(self) -> str:
        from . import redis

        token = '.'.join([
            encode_b66(int.from_bytes(self.id.binary)),
            encode_b66(int((time()*1000)-TOKEN_EPOCH)),
            encode_b66(int(token_hex(20), 16))
        ])

        await redis.delete(
            'token:' + sha256(
                '.'.join(self.token.split('.')[:2]).encode()
            ).hexdigest()
        )

        self.token = hashpw(token.encode(), gensalt()).decode()

        await self.save()

        return token
