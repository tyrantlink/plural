from __future__ import annotations
from .avatar_decoration import AvatarDecorationData
from src.discord.http import request, Route
from typing import TYPE_CHECKING, Literal
from .enums import UserFlags, PremiumType
from src.discord.types import Snowflake
from .base import RawBaseModel

if TYPE_CHECKING:
    from .member import Member


__all__ = ('User',)


class User(RawBaseModel):
    id: Snowflake
    username: str
    discriminator: str
    global_name: str | None = None
    avatar: str | None = None
    bot: bool | None = None
    system: bool | None = None
    mfa_enabled: bool | None = None
    banner: str | None = None
    accent_color: int | None = None
    locale: str | None = None
    verified: bool | None = None
    email: str | None = None
    flags: UserFlags | None = None
    premium_type: PremiumType | None = None
    public_flags: UserFlags | None = None
    avatar_decoration_data: AvatarDecorationData | None = None
    # ? sent with message create event
    member: Member | None = None

    @classmethod
    async def fetch(cls, user_id: Snowflake | Literal['@me']) -> User:
        return cls(
            **await request(
                Route(
                    'GET',
                    '/users/{user_id}',
                    user_id=user_id
                )
            )
        )
