from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from plural.missing import Optional, Nullable

    from src.discord.enums import Permission, RoleFlag
    from src.discord.types import Snowflake


__all__ = (
    'Role',
)


class Role(RawBaseModel):
    class Tags(RawBaseModel):
        # too much effort to model
        # see https://discord.com/developers/docs/topics/permissions#role-object-role-tags-structure
        ...

    id: Snowflake
    """role id"""
    name: str
    """role name"""
    color: int
    """integer representation of hexadecimal color code"""
    hoist: bool
    """if this role is pinned in the user listing"""
    icon: Optional[Nullable[str]]
    """role icon hash"""
    unicode_emoji: Optional[Nullable[str]]
    """role unicode emoji"""
    position: int
    """position of this role (roles with the same position are sorted by id)"""
    permissions: Permission
    """permission bit set"""
    managed: bool
    """whether this role is managed by an integration"""
    mentionable: bool
    """whether this role is mentionable"""
    tags: Optional[Role.Tags]
    """the tags this role has"""
    flags: RoleFlag
    """role flags combined as a bitfield"""
