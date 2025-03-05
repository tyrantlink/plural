from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from src.discord.types import Snowflake


__all__ = (
    'AvatarDecorationData',
)


class AvatarDecorationData(RawBaseModel):
    asset: str
    """the avatar decoration hash"""
    sku_id: Snowflake
    """id of the avatar decoration's SKU"""
