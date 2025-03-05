from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.http import request, Route

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from plural.missing import Optional, Nullable

    from src.discord.enums import UserFlag, PremiumType
    from src.discord.types import Snowflake

    from .avatar_decoration import AvatarDecorationData
    from .guild import Guild


__all__ = (
    'User',
)


class User(RawBaseModel):
    id: Snowflake
    """the user's id"""
    username: str
    """the user's username, not unique across the platform"""
    discriminator: str
    """the user's Discord-tag"""
    global_name: Nullable[str]
    """the user's display name, if it is set. For bots, this is the application name"""
    avatar: Nullable[str]
    """the user's avatar hash"""
    bot: Optional[bool]
    """whether the user belongs to an OAuth2 application"""
    system: Optional[bool]
    """whether the user is an Official Discord System user (part of the urgent message system)"""
    mfa_enabled: Optional[bool]
    """whether the user has two factor enabled on their account"""
    banner: Optional[Nullable[str]]
    """the user's banner hash"""
    accent_color: Optional[Nullable[int]]
    """the user's banner color encoded as an integer representation of hexadecimal color code"""
    locale: Optional[str]
    """the user's chosen language option"""
    verified: Optional[bool]
    """whether the email on this account has been verified"""
    email: Optional[Nullable[str]]
    """the user's email"""
    flags: Optional[UserFlag]
    """the flags on a user's account"""
    premium_type: Optional[PremiumType]
    """the type of Nitro subscription on a user's account"""
    public_flags: Optional[UserFlag]
    """the public flags on a user's account"""
    avatar_decoration_data: Optional[Nullable[AvatarDecorationData]]
    """data for the user's avatar decoration"""

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

    async def fetch_guilds(
        self,
        token: str
    ) -> list[Guild]:
        from .guild import Guild

        return [
            Guild(**guild)
            for guild in
            await request(Route(
                'GET',
                '/users/@me/guilds',
                token=token
            ))
        ]
