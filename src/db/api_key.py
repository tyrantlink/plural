from __future__ import annotations
from beanie import Document
from typing import ClassVar
from pydantic import Field


class ApiKey(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'api_keys'
        validate_on_save = True
        use_state_management = True
        indexes: ClassVar = ['token']

    @classmethod
    def new(cls, user_id: int) -> tuple[ApiKey, str]:
        from src.core.auth import encode_b66, TOKEN_EPOCH
        from bcrypt import hashpw, gensalt
        from secrets import token_hex
        from time import time

        token = '.'.join([
            encode_b66(user_id),
            encode_b66(int((time()*1000)-TOKEN_EPOCH)),
            encode_b66(int(token_hex(20), 16))
        ])
        return (
            ApiKey(
                id=user_id,
                token=hashpw(token.encode(), gensalt()).decode()
            ),
            token
        )

    id: int = Field(  # pyright: ignore #? unknown pyright rule
        description='user id')
    token: str = Field(description='hashed api key')
