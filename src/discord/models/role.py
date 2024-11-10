from .enums import Permission, RoleFlags
from src.discord.types import Snowflake
from .base import RawBaseModel


__all__ = ('RoleSubscriptionData',)


class RoleSubscriptionData(RawBaseModel):
    ...


class RoleTags(RawBaseModel):
    bot_id: Snowflake | None = None
    integration_id: Snowflake | None = None
    premium_subscriber: bool | None = True
    subscription_listing_id: Snowflake | None = None
    available_for_purchase: bool | None = True
    guild_connections: bool | None = True


class Role(RawBaseModel):
    id: Snowflake
    name: str
    color: int
    hoist: bool
    icon: str | None = None
    unicode_emoji: str | None = None
    position: int
    permissions: Permission
    managed: bool
    mentionable: bool
    tags: RoleTags | None = None
    flags: RoleFlags
