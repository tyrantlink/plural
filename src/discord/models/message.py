from __future__ import annotations
from .enums import MessageType, MessageReferenceType, MessageFlags
from .channel import ChannelMention, Channel
from src.discord.http import Route, request
from .sticker import Sticker, StickerItem
from src.discord.types import Snowflake
from .role import RoleSubscriptionData
from .application import Application
from .attachment import Attachment
from .component import Component
from .reaction import Reaction
from .resolved import Resolved
from .base import RawBaseModel
from datetime import datetime
from .guild import Guild
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
    # ? library only, not sent by discord
    channel: Channel | None = None
    guild: Guild | None = None

    async def populate(self) -> None:
        await super().populate()
        if self.channel_id is None:
            return

        self.channel = await Channel.fetch(self.channel_id)

        if self.channel.guild_id is None:
            return

        self.guild = await Guild.fetch(self.channel.guild_id)

    async def delete(self) -> tuple[int, dict] | None:
        return await request(
            Route(
                'DELETE',
                '/channels/{channel_id}/messages/{message_id}',
                channel_id=self.channel_id,
                message_id=self.id
            )
        )

    @classmethod
    async def send(
        cls,
        channel_id: Snowflake,
        content: str | None = None,
        *,
        tts: bool = False,
        embed: Embed | None = None,
        components: list[Component] | None = None,
        sticker_ids: list[Snowflake] | None = None,
        message_reference: MessageReference | None = None,
        allowed_mentions: dict | None = None,
    ) -> Message:
        json = {
            'content': content,
            # 'tts': tts,
            # 'embed': embed.dict() if embed else None,
            # 'components': [c.dict() for c in components] if components else None,
            # 'sticker_ids': sticker_ids,
            # 'message_reference': message_reference.dict() if message_reference else None,
            # 'allowed_mentions': allowed_mentions,
        }

        return cls(
            **await request(
                Route(
                    'POST',
                    '/channels/{channel_id}/messages',
                    channel_id=channel_id
                ),
                json=json
            )
        )
