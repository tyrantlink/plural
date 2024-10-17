from .enums import ChannelType, OverwriteType, VideoQualityMode
from pydantic import BaseModel
from .user import User
from datetime import datetime


class Overwrite(BaseModel):
    id: str
    type: OverwriteType
    allow: int
    deny: int


class ThreadMetadata(BaseModel):
    archived: bool
    auto_archive_duration: int
    archive_timestamp: datetime
    locked: bool
    invitable: bool
    create_timestamp: datetime


class ThreadMember(BaseModel):
    id: str
    user_id: str
    join_timestamp: datetime
    flags: int
    member: dict | None = None  # ? should always be None in this context


class Channel(BaseModel):
    id: str
    type: ChannelType
    guild_id: str | None = None
    position: int | None = None
    permission_overwrites: list[Overwrite] | None = None
    name: str | None = None
    topic: str | None = None
    nsfw: bool | None = None
    last_message_id: str | None = None
    bitrate: int | None = None
    user_limit: int | None = None
    rate_limit_per_user: int | None = None
    recipients: list[User] | None = None
    icon: str | None = None
    owner_id: str | None = None
    application_id: str | None = None
    managed: bool | None = None
    parent_id: str | None = None
    last_pin_timestamp: datetime | None = None
    rtc_region: str | None = None
    video_quality_mode: VideoQualityMode | None = None
    message_count: int | None = None
    member_count: int | None = None
    thread_metadata: ThreadMetadata | None = None
    member: ThreadMember | None = None
    default_auto_archive_duration: int | None = None
    permissions: str | None = None
    flags: int | None = None
    total_message_sent: int | None = None
    available_tags: list[dict] | None = None
    applied_tags: list[str] | None = None
    default_reaction_emoji: dict | None = None
    default_thread_rate_limit_per_user: int | None = None
    default_sort_order: int | None = None
    default_forum_layout: int | None = None
