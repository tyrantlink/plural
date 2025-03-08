from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field
from re import finditer

from plural.db import redis

from src.core.http import request, Route
from src.core.models import env

from src.discord.models.base import RawBaseModel
from src.discord.enums import AllowedMentionType
from src.discord.types import Snowflake

if TYPE_CHECKING:
    from datetime import datetime

    from plural.missing import Optional, Nullable

    from src.discord.enums import MessageType, MessageFlag

    from .expression import Reaction, StickerItem
    from .channel import Channel, ChannelMention
    from .application import Application
    from .attachment import Attachment
    from .component import Component
    from .resolved import Resolved
    from .embed import Embed
    from .poll import Poll
    from .user import User


__all__ = (
    'AllowedMentions',
    'Message',
)


class AllowedMentions(RawBaseModel):
    parse: list[AllowedMentionType] = Field(default_factory=list)
    roles: set[Snowflake] | None = None
    users: set[Snowflake] | None = None
    replied_user: bool | None = None

    @classmethod
    def parse_content(
        cls,
        content: str,
        replied_user: bool = True,
        ignore: set[Snowflake] | None = None
    ) -> AllowedMentions:
        mentions = cls(
            parse=[AllowedMentionType.EVERYONE],
            roles={Snowflake(match.group(1))
                   for match in finditer(r'<@&(\d+)>', content)},
            users={Snowflake(match.group(1))
                   for match in finditer(r'<@!?(\d+)>', content)},
            replied_user=replied_user
        )

        return (
            mentions.strip_mentions(ignore)
            if ignore else
            mentions
        )

    def strip_mentions(self, mentions: set[Snowflake]) -> AllowedMentions:
        _users = self.users or set()
        _roles = self.roles or set()

        for snowflake in mentions:
            if snowflake in _users:
                _users.discard(snowflake)
            if snowflake in _roles:
                _roles.discard(snowflake)

        self.users = _users
        self.roles = _roles

        return self


class Message(RawBaseModel):
    class Activity(RawBaseModel):
        ...

    class Reference(RawBaseModel):
        ...

    class Snapshot(RawBaseModel):
        ...

    class InteractionMetadata(RawBaseModel):
        ...

    class RoleSubscriptionData(RawBaseModel):
        ...

    class Call(RawBaseModel):
        ...

    id: Snowflake
    """id of the message"""
    channel_id: Snowflake
    """id of the channel the message was sent in"""
    author: User
    """the author of this message (not guaranteed to be a valid user, see below)"""
    content: str
    """contents of the message"""
    timestamp: datetime
    """when this message was sent"""
    edited_timestamp: Nullable[datetime]
    """when this message was edited (or null if never)"""
    tts: bool
    """whether this was a TTS message"""
    mention_everyone: bool
    """whether this message mentions everyone"""
    mentions: list[User]
    """users specifically mentioned in the message"""
    mention_roles: list[Snowflake]
    """roles specifically mentioned in this message"""
    mention_channels: Optional[list[ChannelMention]]
    """channels specifically mentioned in this message"""
    attachments: list[Attachment]
    """any attached files"""
    embeds: list[Embed]
    """any embedded content"""
    reactions: Optional[list[Reaction]]
    """reactions to the message"""
    nonce: Optional[int | str]
    """used for validating a message was sent"""
    pinned: bool
    """whether this message is pinned"""
    webhook_id: Optional[Snowflake]
    """if the message is generated by a webhook, this is the webhook's id"""
    type: MessageType
    """type of message"""
    activity: Optional[Message.Activity]
    """sent with Rich Presence-related chat embeds"""
    application: Optional[Application]
    """sent with Rich Presence-related chat embeds"""
    application_id: Optional[Snowflake]
    """if the message is an Interaction or application-owned webhook, this is the id of the application"""
    flags: Optional[MessageFlag]
    """message flags combined as a bitfield* (MessageFlag enum)"""
    message_reference: Optional[Message.Reference]
    """data showing the source of a crosspost, channel follow add, pin, or reply message"""
    message_snapshots: Optional[list[Message.Snapshot]]
    """the message associated with the `message_reference`. This is a minimal subset of fields in a message (e.g. `author` is excluded.)"""
    referenced_message: Optional[Nullable[Message]]
    """the message associated with the message_reference"""
    interaction_metadata: Optional[Message.InteractionMetadata]
    """Sent if the message is sent as a result of an interaction"""
    thread: Optional[Channel]
    """the thread that was started from this message, includes thread member object"""
    components: Optional[list[Component]]
    """sent if the message contains components like buttons, action rows, or other interactive components"""
    sticker_items: Optional[list[StickerItem]]
    """sent if the message contains stickers"""
    position: Optional[int]
    """A generally increasing integer (there may be gaps or duplicates) that represents the approximate position of the message in a thread, it can be used to estimate the relative position of the message in a thread in company with `total_message_sent` on parent thread"""
    role_subscription_data: Optional[Message.RoleSubscriptionData]
    """data of the role subscription purchase or renewal that prompted this ROLE_SUBSCRIPTION_PURCHASE message"""
    resolved: Optional[Resolved]
    """data for users, members, channels, and roles in the message's auto-populated select menus"""
    poll: Optional[Poll]
    """A poll!"""
    call: Optional[Message.Call]
    """the call associated with the message"""

    @classmethod
    async def fetch(
        cls,
        channel_id: Snowflake,
        message_id: Snowflake,
        bot_token: str = env.bot_token
    ) -> Message:
        return cls(**await request(Route(
            'GET',
            '/channels/{channel_id}/messages/{message_id}',
            token=bot_token,
            channel_id=channel_id,
            message_id=message_id
        )))

    async def edit(
        self,
        content: str,
        bot_token: str = env.bot_token
    ) -> Message:
        mentions = AllowedMentions.parse_content(content, False)

        mentions.users &= {user.id for user in self.mentions}
        mentions.roles &= set(self.mention_roles)

        return Message(**await request(
            Route(
                'PATCH',
                '/channels/{channel_id}/messages/{message_id}',
                token=bot_token,
                channel_id=self.channel_id,
                message_id=self.id),
            json={
                'content': content,
                'allowed_mentions': mentions.as_payload()
            })
        )
