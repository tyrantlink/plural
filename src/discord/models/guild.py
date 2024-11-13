from __future__ import annotations
from .enums import Permission, VerificationLevel, DefaultMessageNotificationLevel, ExplicitContentFilterLevel, GuildFeature, MFALevel, SystemChannelFlag, PremiumTier, NSFWLevel
from pydantic import model_validator, field_validator
from src.discord.http import Route, request
from src.discord.types import Snowflake
from .base import RawBaseModel
from .sticker import Sticker
from .emoji import Emoji
from .role import Role
import logfire


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
    name: str | None = None
    icon: str | None = None
    icon_hash: str | None = None
    splash: str | None = None
    discovery_splash: str | None = None
    owner: bool | None = None
    owner_id: Snowflake | None = None
    permissions: Permission | None = None
    region: str | None = None  # deprecated
    afk_channel_id: Snowflake | None = None
    afk_timeout: int | None = None
    widget_enabled: bool | None = None
    widget_channel_id: Snowflake | None = None
    verification_level: VerificationLevel | None = None
    default_message_notifications: DefaultMessageNotificationLevel | None = None
    explicit_content_filter: ExplicitContentFilterLevel | None = None
    roles: list[Role] | None = None
    emojis: list[Emoji] | None = None
    features: list[GuildFeature]
    mfa_level: MFALevel | None = None
    application_id: Snowflake | None = None
    system_channel_id: Snowflake | None = None
    system_channel_flags: SystemChannelFlag | None = None
    rules_channel_id: Snowflake | None = None
    max_presences: int | None = None
    max_members: int | None = None
    vanity_url_code: str | None = None
    description: str | None = None
    banner: str | None = None
    premium_tier: PremiumTier
    premium_subscription_count: int | None = None
    preferred_locale: str | None = None
    public_updates_channel_id: Snowflake | None = None
    max_video_channel_users: int | None = None
    max_stage_video_channel_users: int | None = None
    approximate_member_count: int | None = None
    approximate_presence_count: int | None = None
    welcome_screen: WelcomeScreen | None = None
    nsfw_level: NSFWLevel | None = None
    stickers: list[Sticker] | None = None
    premium_progress_bar_enabled: bool | None = None
    safety_alerts_channel_id: Snowflake | None = None

    @model_validator(mode='before')
    def _ensure_premium_tier(cls, data: dict) -> dict:
        if (
            data.get('premium_tier') is not None or
            (features := data.get('features')) is None
        ):
            return data

        data['premium_tier'] = (
            PremiumTier.TIER_3
            if 'ANIMATED_BANNER' in features else
            PremiumTier.TIER_2
            if 'BANNER' in features else
            PremiumTier.TIER_1
            if 'ANIMATED_ICON' in features else
            PremiumTier.NONE
        )

        return data

    @field_validator('features', mode='before')
    @classmethod
    def validate_guild_feature(cls, v):
        features = []
        for feature in v:
            if feature in GuildFeature.__members__:
                features.append(GuildFeature(feature))
                continue

            logfire.warn(
                'Unknown enum value \'{value}\' for {class_name}',
                value=feature,
                class_name=GuildFeature.__name__
            )

        return features

    @property
    def filesize_limit(self) -> int:
        return self.premium_tier.filesize_limit

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
