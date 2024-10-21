from .attachment import Attachment
from .resolved import ResolvedData
from pydantic import BaseModel
from datetime import datetime
from .channel import Channel
from .user import User


class Message(BaseModel):
    id: str
    channel_id: str
    author: User | None = None
    content: str
    timestamp: datetime
    edited_timestamp: datetime | None = None
    tts: bool
    mention_everyone: bool
    mentions: list[User]
    mention_roles: list[str]
    mention_channels: list[dict] | None = None
    attachments: list[Attachment]
    embeds: list[dict]
    reactions: list[dict] | None = None
    nonce: str | int | None = None
    pinned: bool
    webhook_id: str | None = None
    type: int
    activity: dict | None = None
    application: dict | None = None
    application_id: str | None = None
    flags: int | None = None
    message_reference: dict | None = None
    message_snapshots: list[dict] | None = None
    referenced_message: dict | None = None
    interaction_metadata: dict | None = None
    interaction: dict | None = None  # ? deprecated; use interaction_metadata
    thread: Channel | None = None
    components: list[dict] | None = None
    sticker_items: list[dict] | None = None
    stickers: list[dict] | None = None
    position: int | None = None
    role_subscription_data: dict | None = None
    resolved: ResolvedData | None = None
    poll: dict | None = None
    call: dict | None = None
