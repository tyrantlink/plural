from __future__ import annotations
from .attachment import Attachment
from typing import TYPE_CHECKING
from pydantic import BaseModel
from .channel import Channel
from .member import Member
from .user import User


if TYPE_CHECKING:
    from .message import Message


class ResolvedData(BaseModel):
    users: dict[str, User] | None = None
    members: dict[str, Member] | None = None
    roles: dict[str, dict] | None = None
    channels: dict[str, Channel] | None = None
    messages: dict[str, Message] | None = None
    attachments: dict[str, Attachment] | None = None
