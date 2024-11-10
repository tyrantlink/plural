from __future__ import annotations
from .enums import Permission, VerificationLevel, DefaultMessageNotificationLevel, ExplicitContentFilterLevel, GuildFeature, MFALevel, SystemChannelFlags, PremiumTier, NSFWLevel
from src.discord.http import Route, request
from src.discord.types import Snowflake
from .base import RawBaseModel
from .sticker import Sticker
from typing import Annotated
from .emoji import Emoji
from .role import Role


class WelcomeScreenChannel(RawBaseModel):
    channel_id: Snowflake
    description: str
    emoji_id: Snowflake | None = None
    emoji_name: str | None = None


class WelcomeScreen(RawBaseModel):
    description: str
    welcome_channels: list[WelcomeScreenChannel]


class Guild(RawBaseModel):
    id: Snowflake
    name: str
    icon: str | None = None
    icon_hash: str | None = None
    splash: str | None = None
    discovery_splash: str | None = None
    owner: bool | None = None
    owner_id: Snowflake
    permissions: Permission | None = None
    region: str | None = None  # deprecated
    afk_channel_id: Snowflake | None = None
    afk_timeout: int
    widget_enabled: bool | None = None
    widget_channel_id: Snowflake | None = None
    verification_level: VerificationLevel
    default_message_notifications: DefaultMessageNotificationLevel
    explicit_content_filter: ExplicitContentFilterLevel
    roles: list[Role]
    emojis: list[Emoji]
    features: list[GuildFeature]
    mfa_level: MFALevel
    application_id: Snowflake | None = None
    system_channel_id: Snowflake | None = None
    system_channel_flags: SystemChannelFlags
    rules_channel_id: Snowflake | None = None
    max_presences: int | None = None
    max_members: int | None = None
    vanity_url_code: str | None = None
    description: str | None = None
    banner: str | None = None
    premium_tier: PremiumTier
    premium_subscription_count: int | None = None
    preferred_locale: str
    public_updates_channel_id: Snowflake | None = None
    max_video_channel_users: int | None = None
    max_stage_video_channel_users: int | None = None
    approximate_member_count: int | None = None
    approximate_presence_count: int | None = None
    welcome_screen: WelcomeScreen | None = None
    nsfw_level: NSFWLevel
    stickers: list[Sticker] | None = None
    premium_progress_bar_enabled: bool
    safety_alerts_channel_id: Snowflake | None = None

    @classmethod
    async def fetch(cls, guild_id: Snowflake) -> Guild:
        return cls(
            **await request(
                Route(
                    'GET',
                    '/guilds/{guild_id}',
                    guild_id=guild_id
                )
            )
        )
