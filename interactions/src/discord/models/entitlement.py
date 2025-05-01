from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from datetime import datetime

    from plural.missing import Optional, Nullable

    from src.discord.types import Snowflake
    from src.discord.enums import EntitlementType


class Entitlement(RawBaseModel):
    id: Snowflake
    """ID of the entitlement"""
    sku_id: Snowflake
    """ID of the SKU"""
    application_id: Snowflake
    """ID of the parent application"""
    user_id: Optional[Snowflake]
    """ID of the user that is granted access to the entitlement's sku"""
    type: EntitlementType
    """Type of entitlement"""
    deleted: bool
    """Entitlement was deleted"""
    starts_at: Nullable[datetime]
    """Start date at which the entitlement is valid."""
    ends_at: Nullable[datetime]
    """Date at which the entitlement is no longer valid."""
    guild_id: Optional[Snowflake]
    """ID of the guild that is granted access to the entitlement's sku"""
    consumed: Optional[bool]
    """For consumable items, whether or not the entitlement has been consumed"""
