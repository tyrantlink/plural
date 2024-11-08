from .avatar_decoration import AvatarDecorationData
from .enums import GuildMemberFlags
from .base import RawBaseModel
from datetime import datetime
from .types import Snowflake
from .user import User

__all__ = ('Member',)


class Member(RawBaseModel):
    user: User | None = None
    nick: str | None = None
    avatar: str | None = None
    banner: str | None = None
    roles: list[Snowflake] | None = None
    joined_at: datetime | None = None
    premium_since: datetime | None = None
    deaf: bool | None = None
    mute: bool | None = None
    flags: GuildMemberFlags
    pending: bool | None = None
    permissions: str | None = None  # ! make this a Permission object
    communication_disabled_until: datetime | None = None
    avatar_decoration_data: AvatarDecorationData | None = None
