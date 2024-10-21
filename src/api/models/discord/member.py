from pydantic import BaseModel
from datetime import datetime
from .user import User
from typing import Any


class Member(BaseModel):
    user: User | None = None
    nick: str | None = None
    avatar: str | None = None
    roles: list[str]
    joined_at: datetime
    premium_since: datetime | None = None
    deaf: bool | None = None
    mute: bool | None = None
    flags: int
    pending: bool | None = None
    permissions: str | None = None
    # ? not typed in the discord api docs
    banner: Any | None = None
    communication_disabled_until: Any | None = None
    unusual_dm_activity_until: Any | None = None
