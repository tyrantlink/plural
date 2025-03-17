from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

from src.discord.enums import ChannelType

if TYPE_CHECKING:
    from datetime import datetime

    from plural.missing import Optional, Nullable
    from src.discord.types import Snowflake

    from src.discord.enums import (
        VideoQualityMode,
        ForumLayoutType,
        OverwriteType,
        SortOrderType,
        ChannelFlag,
        Permission
    )

    from .member import Member
    from .user import User


__all__ = (
    'Channel',
    'ChannelMention',
)


class Channel(RawBaseModel):
    class Overwrite(RawBaseModel):
        id: Snowflake
        """role or user id"""
        type: OverwriteType
        """either 0 (role) or 1 (member)"""
        allow: Permission
        """permission bit set* (Permission enum)"""
        deny: Permission
        """permission bit set* (Permission enum)"""

    class ThreadMetadata(RawBaseModel):
        archived: bool
        """whether the thread is archived"""
        auto_archive_duration: int
        """the thread will stop showing in the channel list after `auto_archive_duration` minutes of inactivity, can be set to: 60, 1440, 4320, 10080"""
        archive_timestamp: datetime
        """timestamp when the thread's archive status was last changed, used for calculating recent activity"""
        locked: bool
        """whether the thread is locked; when a thread is locked, only users with MANAGE_THREADS can unarchive it"""
        invitable: Optional[bool]
        """whether non-moderators can add other non-moderators to a thread; only available on private threads"""
        create_timestamp: Optional[Nullable[datetime]]
        """timestamp when the thread was created; only populated for threads created after 2022-01-09"""

    class ThreadMember(RawBaseModel):
        id: Snowflake
        """ID of the thread"""
        user_id: Optional[Snowflake]
        """ID of the user"""
        join_timestamp: datetime
        """Time the user last joined the thread"""
        flags: int
        """Any user-thread settings, currently only used for notifications"""
        member: Optional[Member]
        """Additional information about the user"""

    class DefaultReaction(RawBaseModel):
        emoji_id: Nullable[Snowflake]
        """the id of a guild's custom emoji"""
        emoji_name: Nullable[str]
        """the unicode character of the emoji"""

    class ForumTag(RawBaseModel):
        id: Snowflake
        """the id of the tag"""
        name: str
        """the name of the tag (0-20 characters)"""
        moderated: bool
        """whether this tag can only be added to or removed from threads by a member with the `MANAGE_THREADS` permission"""
        emoji_id: Nullable[Snowflake]
        """the id of a guild's custom emoji"""
        emoji_name: Nullable[str]
        """the unicode character of the emoji"""

    id: Snowflake
    """the id of this channel"""
    type: ChannelType
    """the type of channel"""
    guild_id: Optional[Snowflake]
    """the id of the guild (may be missing for some channel objects received over gateway guild dispatches)"""
    position: Optional[int]
    """sorting position of the channel (channels with the same position are sorted by id)"""
    permission_overwrites: Optional[list[Channel.Overwrite]]
    """explicit permission overwrites for members and roles"""
    name: Optional[Nullable[str]]
    """the name of the channel (1-100 characters)"""
    topic: Optional[Nullable[str]]
    """the channel topic (0-4096 characters for `GUILD_FORUM` and `GUILD_MEDIA` channels, 0-1024 characters for all others)"""
    nsfw: Optional[bool]
    """whether the channel is nsfw"""
    last_message_id: Optional[Nullable[Snowflake]]
    """the id of the last message sent in this channel (or thread for `GUILD_FORUM` or `GUILD_MEDIA` channels) (may not point to an existing or valid message or thread)"""
    bitrate: Optional[int]
    """the bitrate (in bits) of the voice channel"""
    user_limit: Optional[int]
    """the user limit of the voice channel"""
    rate_limit_per_user: Optional[int]
    """amount of seconds a user has to wait before sending another message (0-21600); bots, as well as users with the permission `manage_messages` or `manage_channel`, are unaffected"""
    recipients: Optional[list[User]]
    """the recipients of the DM"""
    icon: Optional[Nullable[str]]
    """icon hash of the group DM"""
    owner_id: Optional[Snowflake]
    """id of the creator of the group DM or thread"""
    application_id: Optional[Snowflake]
    """application id of the group DM creator if it is bot-created"""
    managed: Optional[bool]
    """for group DM channels: whether the channel is managed by an application via the `gdm.join` OAuth2 scope"""
    parent_id: Optional[Nullable[Snowflake]]
    """for guild channels: id of the parent category for a channel (each parent category can contain up to 50 channels), for threads: id of the text channel this thread was created"""
    last_pin_timestamp: Optional[Nullable[datetime]]
    """when the last pinned message was pinned. This may be `null` in events such as `GUILD_CREATE` when a message is not pinned."""
    rtc_region: Optional[Nullable[str]]
    """voice region id for the voice channel, automatic when set to null"""
    video_quality_mode: Optional[VideoQualityMode]
    """the camera video quality mode of the voice channel, 1 when not present"""
    message_count: Optional[int]
    """number of messages (not including the initial message or deleted messages) in a thread."""
    member_count: Optional[int]
    """an approximate count of users in a thread, stops counting at 50"""
    thread_metadata: Optional[Channel.ThreadMetadata]
    """thread-specific fields not needed by other channels"""
    member: Optional[Channel.ThreadMember]
    """thread member object for the current user, if they have joined the thread, only included on certain API endpoints"""
    default_auto_archive_duration: Optional[int]
    """default duration, copied onto newly created threads, in minutes, threads will stop showing in the channel list after the specified period of inactivity, can be set to: 60, 1440, 4320, 10080"""
    permissions: Optional[str]
    """computed permissions for the invoking user in the channel, including overwrites, only included when part of the `resolved` data received on a slash command interaction. This does not include implicit permissions, which may need to be checked separately"""
    flags: Optional[ChannelFlag]
    """channel flags combined as a bitfield* (ChannelFlag enum)"""
    total_message_sent: Optional[int]
    """number of messages ever sent in a thread, it's similar to `message_count` on message creation, but will not decrement the number when a message is deleted"""
    available_tags: Optional[list[Channel.ForumTag]]
    """the set of tags that can be used in a `GUILD_FORUM` or a `GUILD_MEDIA` channel"""
    applied_tags: Optional[list[Snowflake]]
    """the IDs of the set of tags that have been applied to a thread in a `GUILD_FORUM` or a `GUILD_MEDIA` channel"""
    default_reaction_emoji: Optional[Channel.DefaultReaction]
    """the emoji to show in the add reaction button on a thread in a `GUILD_FORUM` or a `GUILD_MEDIA` channel"""
    default_thread_rate_limit_per_user: Optional[int]
    """the initial `rate_limit_per_user` to set on newly created threads in a channel. this field is copied to the thread at creation time and does not live update."""
    default_sort_order: Optional[Nullable[SortOrderType]]
    """the default sort order type used to order posts in `GUILD_FORUM` and `GUILD_MEDIA` channels. Defaults to `null`, which indicates a preferred sort order hasn't been set by a channel admin"""
    default_forum_layout: Optional[ForumLayoutType]
    """the default forum layout view used to display posts in `GUILD_FORUM` channels. Defaults to `0`, which indicates a layout view has not been set by a channel admin"""

    @property
    def mention(self) -> str:
        return f'<#{self.id}>'

    @property
    def is_thread(self) -> bool:
        return self.type in (
            ChannelType.PUBLIC_THREAD,
            ChannelType.PRIVATE_THREAD
        )


class ChannelMention(RawBaseModel):
    id: Snowflake
    """id of the channel"""
    guild_id: Snowflake
    """id of the guild containing the channel"""
    type: ChannelType
    """the type of channel"""
    name: str
    """the name of the channel"""
