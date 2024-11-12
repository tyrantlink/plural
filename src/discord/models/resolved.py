from src.discord.types import Snowflake
from .attachment import Attachment
from typing import TYPE_CHECKING
from .base import RawBaseModel
from typing import ForwardRef
from .channel import Channel
from .member import Member
from .user import User
from .role import Role


MessageRef = ForwardRef('Message')


class Resolved(RawBaseModel):
    users: dict[Snowflake, User] | None = None
    members: dict[Snowflake, Member] | None = None
    roles: dict[Snowflake, Role] | None = None
    channels: dict[Snowflake, Channel] | None = None
    if TYPE_CHECKING:
        from .message import Message
        messages: dict[Snowflake, Message]
    else:
        messages: dict[Snowflake, MessageRef] | None = None
    attachments: dict[Snowflake, Attachment] | None = None
