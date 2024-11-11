from src.discord.types import Snowflake
from typing import TYPE_CHECKING
from .base import RawBaseModel

# if TYPE_CHECKING:
from .attachment import Attachment
# from .message import Message
from .channel import Channel
from .member import Member
from .user import User
from .role import Role


__all__ = ('Resolved',)


class Resolved(RawBaseModel):
    users: dict[Snowflake, User] | None = None
    members: dict[Snowflake, Member] | None = None
    roles: dict[Snowflake, Role] | None = None
    channels: dict[Snowflake, Channel] | None = None
    # messages: dict[Snowflake, Message] | None = None
    attachments: dict[Snowflake, Attachment] | None = None
