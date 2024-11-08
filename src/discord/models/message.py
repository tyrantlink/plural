from __future__ import annotations
from .enums import MessageType, MessageReferenceType, MessageFlags
from .channel import ChannelMention, Channel
from .sticker import Sticker, StickerItem
from .role import RoleSubscriptionData
from .application import Application
from .attachment import Attachment
from .component import Component
from .reaction import Reaction
from .resolved import Resolved
from .base import RawBaseModel
from datetime import datetime
from .types import Snowflake
from .member import Member
from .embed import Embed
from .user import User
from .poll import Poll


__all__ = (
    'MessageActivity',
    'MessageReference',
    'MessageInteractionMetadata',
    'MessageInteraction',
    'MessageCall',
    'Message',
)


class MessageActivity(RawBaseModel):
    ...


class MessageReference(RawBaseModel):
    type: MessageReferenceType = MessageReferenceType.DEFAULT
    message_id: Snowflake | None = None
    channel_id: Snowflake | None = None
    guild_id: Snowflake | None = None
    fail_if_not_exists: bool = True


class MessageInteractionMetadata(RawBaseModel):
    ...


class MessageInteraction(RawBaseModel):
    ...  # deprecated


class MessageCall(RawBaseModel):
    participants: list[Snowflake]
    ended_timestamp: datetime | None = None


class Message(RawBaseModel):
    id: Snowflake
    channel_id: Snowflake
    author: User | None = None
    content: str
    timestamp: datetime
    edited_timestamp: datetime | None = None
    tts: bool | None = None
    mention_everyone: bool
    mentions: list[User]
    mention_roles: list[Snowflake]
    mention_channels: list[ChannelMention] | None = None
    attachments: list[Attachment]
    embeds: list[Embed]
    reactions: list[Reaction] | None = None
    nonce: int | str | None = None
    pinned: bool
    webhook_id: Snowflake | None = None
    type: MessageType
    activity: MessageActivity | None = None
    application: Application | None = None
    application_id: Snowflake | None = None
    flags: MessageFlags
    message_reference: MessageReference | None = None
    message_snapshots: list[Message] | None = None
    referenced_message: Message | None = None
    interaction_metadata: MessageInteractionMetadata | None = None
    interaction: MessageInteraction | None = None  # deprecated
    thread: Channel | None = None
    components: list[Component] | None = None
    sticker_items: list[StickerItem] | None = None
    stickers: list[Sticker] | None = None  # deprecated
    position: int | None = None
    role_subscription_data: list[RoleSubscriptionData] | None = None
    resolved: Resolved | None = None
    poll: Poll | None = None
    call: MessageCall | None = None
