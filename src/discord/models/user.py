from __future__ import annotations
from .avatar_decoration import AvatarDecorationData
from src.discord.http import request, Route
from typing import TYPE_CHECKING, Literal
from .enums import UserFlag, PremiumType
from src.discord.types import Snowflake
from .base import RawBaseModel

if TYPE_CHECKING:
    from .member import Member


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
    flags: UserFlag | None = None
    premium_type: PremiumType | None = None
    public_flags: UserFlag | None = None
    avatar_decoration_data: AvatarDecorationData | None = None
    # ? sent with message create event
    member: Member | None = None

    @property
    def mention(self) -> str:
        return f'<@{self.id}>'

    @property
    def display_name(self) -> str:
        return self.global_name or self.username

    @property
    def default_avatar_url(self) -> str:
        avatar = (
            (self.id >> 22) % 6
            if self.discriminator in {None, '0000'} else
            int(self.discriminator) % 5)

        return f'https://cdn.discordapp.com/embed/avatars/{avatar}.png'

    @property
    def avatar_url(self) -> str:
        if self.avatar is None:
            return self.default_avatar_url

        return 'https://cdn.discordapp.com/avatars/{id}/{avatar}.{format}?size=1024'.format(
            id=self.id,
            avatar=self.avatar,
            format='gif' if self.avatar.startswith('a_') else 'png'
        )

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
