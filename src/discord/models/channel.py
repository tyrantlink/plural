from __future__ import annotations
from .enums import ChannelType, OverwriteType, VideoQualityMode, ChannelFlags, Permission
from src.discord.http import Route, request
from src.discord.types import Snowflake
from .base import RawBaseModel
from datetime import datetime
from .user import User

__all__ = (
    'ChannelMention',
    'Channel',
)


class ChannelMention(RawBaseModel):
    id: Snowflake
    guild_id: Snowflake
    type: ChannelType
    name: str


class Overwrite(RawBaseModel):
    id: Snowflake
    type: OverwriteType
    allow: Permission
    deny: Permission


class ThreadMetadata(RawBaseModel):
    ...


class ThreadMember(RawBaseModel):
    ...


class ForumTag(RawBaseModel):
    id: Snowflake
    name: str
    moderated: bool
    emoji_id: Snowflake | None = None
    emoji_name: str | None = None


class DefaultReaction(RawBaseModel):
    emoji_id: Snowflake | None = None
    emoji_name: str | None = None


class Channel(RawBaseModel):
    id: Snowflake
    type: ChannelType | None = None
    guild_id: Snowflake | None = None
    position: int | None = None
    permission_overwrites: list[Overwrite] | None = None
    name: str | None = None
    topic: str | None = None
    nsfw: bool | None = None
    last_message_id: Snowflake | None = None
    bitrate: int | None = None
    user_limit: int | None = None
    rate_limit_per_user: int | None = None
    recipients: list[User] | None = None
    icon: str | None = None
    owner_id: Snowflake | None = None
    application_id: Snowflake | None = None
    managed: bool | None = None
    parent_id: Snowflake | None = None
    last_pin_timestamp: datetime | None = None
    rtc_region: str | None = None
    video_quality_mode: VideoQualityMode | None = None
    message_count: int | None = None
    member_count: int | None = None
    thread_metadata: ThreadMetadata | None = None
    member: ThreadMember | None = None
    default_auto_archive_duration: int | None = None
    permissions: Permission | None = None
    flags: ChannelFlags | None = None
    total_message_sent: int | None = None
    available_tags: list[ForumTag] | None = None
    applied_tags: list[Snowflake] | None = None
    default_reaction_emoji: DefaultReaction | None = None
    default_thread_rate_limit_per_user: int | None = None
    default_sort_order: int | None = None
    default_forum_layout: int | None = None

    @classmethod
    async def fetch(cls, channel_id: Snowflake) -> Channel:
        return cls(
            **await request(
                Route(
                    'GET',
                    '/channels/{channel_id}',
                    channel_id=channel_id
                )
            )
        )
