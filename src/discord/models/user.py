from __future__ import annotations
from .avatar_decoration import AvatarDecorationData
from .enums import UserFlags, PremiumType
from typing import TYPE_CHECKING
from .base import RawBaseModel
from .types import Snowflake

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
