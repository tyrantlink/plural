from src.discord.types import Snowflake
from .base import RawBaseModel


class AvatarDecorationData(RawBaseModel):
    asset: str
    sku_id: Snowflake
