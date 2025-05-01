from __future__ import annotations

from typing import TYPE_CHECKING

from plural.missing import is_not_missing, MISSING

from src.core.http import request, Route

from src.discord.models.base import RawBaseModel, DiscordCache

if TYPE_CHECKING:
    from plural.missing import Optional, Nullable
    from src.discord.types import Snowflake

    from src.discord.enums import (
        DefaultMessageNotificationLevel,
        ExplicitContentFilterLevel,
        SystemChannelFlag,
        VerificationLevel,
        PremiumTier,
        Permission,
        NSFWLevel,
        MFALevel
    )

    from .expression import Emoji, Sticker
    from .role import Role


__all__ = (
    'Guild',
)


class Guild(RawBaseModel):
    class WelcomeScreen(RawBaseModel):
        class Channel(RawBaseModel):
            channel_id: Snowflake
            description: str
            emoji_id: Nullable[Snowflake]
            emoji_name: Nullable[str]

        description: Nullable[str]
        welcome_channels: list[Guild.WelcomeScreen.Channel]

    id: Snowflake
    """guild id"""
    name: Optional[str]
    """guild name (2-100 characters, excluding trailing and leading whitespace)"""
    icon: Optional[Nullable[str]]
    """icon hash"""
    icon_hash: Optional[Nullable[str]]
    """icon hash, returned when in the template object"""
    splash: Optional[Nullable[str]]
    """splash hash"""
    discovery_splash: Optional[Nullable[str]]
    """discovery splash hash; only present for guilds with the "DISCOVERABLE" feature"""
    owner: Optional[bool]
    """true if the user is the owner of the guild"""
    owner_id: Optional[Snowflake]
    """id of owner"""
    permissions: Optional[Permission]
    """total permissions for the user in the guild (excludes overwrites and implicit permissions)"""
    region: Optional[str]
    """voice region id for the guild (deprecated)"""
    afk_channel_id: Optional[Nullable[Snowflake]]
    """id of afk channel"""
    afk_timeout: Optional[int]
    """afk timeout in seconds"""
    widget_enabled: Optional[bool]
    """true if the server widget is enabled"""
    widget_channel_id: Optional[Nullable[Snowflake]]
    """the channel id that the widget will generate an invite to, or `null` if set to no invite"""
    verification_level: Optional[VerificationLevel]
    """verification level required for the guild"""
    default_message_notifications: Optional[DefaultMessageNotificationLevel]
    """default message notifications level"""
    explicit_content_filter: Optional[ExplicitContentFilterLevel]
    """explicit content filter level"""
    roles: Optional[list[Role]]
    """roles in the guild"""
    emojis: Optional[list[Emoji]]
    """custom guild emojis"""
    features: list[str]
    """enabled guild features"""
    mfa_level: Optional[MFALevel]
    """required MFA level for the guild"""
    application_id: Optional[Nullable[Snowflake]]
    """application id of the guild creator if it is bot-created"""
    system_channel_id: Optional[Nullable[Snowflake]]
    """the id of the channel where guild notices such as welcome messages and boost events are posted"""
    system_channel_flags: Optional[SystemChannelFlag]
    """system channel flags"""
    rules_channel_id: Optional[Nullable[Snowflake]]
    """the id of the channel where Community guilds can display rules and/or guidelines"""
    max_presences: Optional[Nullable[int]]
    """the maximum number of presences for the guild (`null` is always returned, apart from the largest of guilds)"""
    max_members: Optional[int]
    """the maximum number of members for the guild"""
    vanity_url_code: Optional[Nullable[str]]
    """the vanity url code for the guild"""
    description: Optional[Nullable[str]]
    """the description of a guild"""
    banner: Optional[Nullable[str]]
    """banner hash"""
    premium_tier: Optional[PremiumTier]
    """premium tier (Server Boost level)"""
    premium_subscription_count: Optional[int]
    """the number of boosts this guild currently has"""
    preferred_locale: Optional[str]
    """the preferred locale of a Community guild; used in server discovery and notices from Discord, and sent in interactions; defaults to "en-US" """
    public_updates_channel_id: Optional[Nullable[Snowflake]]
    """the id of the channel where admins and moderators of Community guilds receive notices from Discord"""
    max_video_channel_users: Optional[int]
    """the maximum amount of users in a video channel"""
    max_stage_video_channel_users: Optional[int]
    """the maximum amount of users in a stage video channel"""
    approximate_member_count: Optional[int]
    """approximate number of members in this guild, returned from the `GET /guilds/<id>` and `/users/@me/guilds` endpoints when `with_counts` is `true`"""
    approximate_presence_count: Optional[int]
    """approximate number of non-offline members in this guild, returned from the `GET /guilds/<id>` and `/users/@me/guilds` endpoints when `with_counts` is `true`"""
    welcome_screen: Optional[Guild.WelcomeScreen]
    """the welcome screen of a Community guild, shown to new members, returned in an Invite's guild object"""
    nsfw_level: Optional[NSFWLevel]
    """guild NSFW level"""
    stickers: Optional[list[Sticker]]
    """custom guild stickers"""
    premium_progress_bar_enabled: Optional[bool]
    """whether the guild has the boost progress bar enabled"""
    safety_alerts_channel_id: Optional[Nullable[Snowflake]]
    """the id of the channel where admins and moderators of Community guilds receive safety alerts from Discord"""

    @property
    def icon_url(self) -> str | None:
        if not self.icon:
            return None

        return f'https://cdn.discordapp.com/icons/{self.id}/{self.icon}.webp'

    @property
    def filesize_limit(self) -> int:
        return (
            self.premium_tier.filesize_limit
            if is_not_missing(self.premium_tier)
            else 10_485_760
        )

    async def populate(self, roles: set[str] | None = None) -> None:
        await super().populate()

        if not self.roles:
            self.roles = await self.fetch_roles(roles)

    @classmethod
    async def fetch(cls, id: Snowflake | int) -> Guild | None:
        cache = await DiscordCache.fetch(f'guild:{id}')

        if not (cache and cache.valid):
            return None

        guild = cls(**cache.data)

        await guild.populate()

        return guild

    async def fetch_roles(self, roles: set[str] | None = None) -> list[Role]:
        roles = roles or set()

        #! this might not need to be finished
        return []

    async def modify_current_member(
        self,
        token: str,
        nick: Optional[Nullable[str]] = MISSING,
    ) -> None:
        await request(
            Route(
                'PATCH',
                '/guilds/{guild_id}/members/@me',
                guild_id=self.id,
                token=token),
            json=(
                {'nick': nick}
                if is_not_missing(nick) else
                {}
            )
        )
