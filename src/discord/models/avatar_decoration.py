from .base import RawBaseModel
from .types import Snowflake

__all__ = ('AvatarDecorationData',)


class AvatarDecorationData(RawBaseModel):
    asset: str
    sku_id: Snowflake
