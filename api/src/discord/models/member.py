from __future__ import annotations

from typing import TYPE_CHECKING

from plural.missing import is_not_missing

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from datetime import datetime

    from plural.missing import Optional, Nullable

    from src.discord.enums import MemberFlag, Permission
    from src.discord.types import Snowflake

    from .avatar_decoration import AvatarDecorationData
    from .user import User


__all__ = (
    'Member',
)


class Member(RawBaseModel):
    user: Optional[User]
    """the user this guild member represents"""
    nick: Optional[Nullable[str]]
    """this user's guild nickname"""
    avatar: Optional[Nullable[str]]
    """the member's guild avatar hash"""
    banner: Optional[Nullable[str]]
    """the member's guild banner hash"""
    roles: list[Snowflake]
    """array of role object ids"""
    joined_at: datetime
    """when the user joined the guild"""
    premium_since: Optional[Nullable[datetime]]
    """when the user started boosting the guild"""
    deaf: Optional[bool]
    """whether the user is deafened in voice channels\n\nmay be missing in some partials"""
    mute: Optional[bool]
    """whether the user is muted in voice channels\n\nmay be missing in some partials"""
    flags: MemberFlag
    """guild member flags represented as a bit set (MemberFlag object), defaults to `0`"""
    pending: Optional[bool]
    """whether the user has not yet passed the guild's Membership Screening requirements"""
    permissions: Permission
    """total permissions of the member in the channel, including overwrites, returned when in the interaction object"""
    communication_disabled_until: Optional[Nullable[datetime]]
    """when the user's timeout will expire and the user will be able to communicate in the guild again, null or a time in the past if the user is not timed out"""
    avatar_decoration_data: Optional[Nullable[AvatarDecorationData]]
    """data for the member's guild avatar decoration"""

    @property
    def display_name(self) -> str:
        if not is_not_missing(self.user):
            raise ValueError('Member is missing user data')

        return (
            self.nick or
            self.user.global_name or
            self.user.username
        )

    @property
    def default_avatar_url(self) -> str:
        if not is_not_missing(self.user):
            raise ValueError('Member is missing user data')

        avatar = (
            (self.id >> 22) % 6
            if self.user.discriminator in {None, '0000'} else
            int(self.user.discriminator) % 5)

        return f'https://cdn.discordapp.com/embed/avatars/{avatar}.png'

    @property
    def avatar_url(self) -> str:
        if not is_not_missing(self.user):
            raise ValueError('Member is missing user data')

        avatar = self.avatar or self.user.avatar

        if not is_not_missing(avatar) or avatar is None:
            return self.default_avatar_url

        return 'https://cdn.discordapp.com/avatars/{id}/{avatar}.{format}?size=1024'.format(
            id=self.user.id,
            avatar=avatar,
            format='gif' if avatar.startswith('a_') else 'png'
        )
