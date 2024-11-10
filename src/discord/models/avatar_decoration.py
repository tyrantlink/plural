from src.discord.types import Snowflake
from .base import RawBaseModel

__all__ = ('AvatarDecorationData',)


class AvatarDecorationData(RawBaseModel):
    asset: str
    sku_id: Snowflake
