from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from src.discord.types import Snowflake
    from plural.missing import Optional

    from .attachment import Attachment
    from .message import Message
    from .channel import Channel
    from .member import Member
    from .role import Role
    from .user import User


__all__ = (
    'Resolved',
)


class Resolved(RawBaseModel):
    users: Optional[dict[Snowflake, User]]
    """IDs and User objects"""
    members: Optional[dict[Snowflake, Member]]
    """IDs and partial Member objects"""
    roles: Optional[dict[Snowflake, Role]]
    """IDs and Role objects"""
    channels: Optional[dict[Snowflake, Channel]]
    """IDs and partial Channel objects"""
    messages: Optional[dict[Snowflake, Message]]
    """IDs and partial Message objects"""
    attachments: Optional[dict[Snowflake, Attachment]]
    """IDs and attachment objects"""
