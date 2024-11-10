from src.discord.types import Snowflake
from .enums import WebhookType
from .base import RawBaseModel
from .channel import Channel
from .guild import Guild
from .user import User


class Webhook(RawBaseModel):
    id: Snowflake
    type: WebhookType
    guild_id: Snowflake | None = None
    channel_id: Snowflake | None
    user: User | None = None
    name: str | None
    avatar: str | None
    token: str | None = None
    application_id: Snowflake | None = None
    source_guild: Guild | None = None
    source_channel: Channel | None = None
    url: str | None = None
