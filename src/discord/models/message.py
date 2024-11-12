from __future__ import annotations
from .enums import MessageType, MessageReferenceType, MessageFlag, AllowedMentionType
from src.discord.http import Route, request, File
from asyncio import get_event_loop, create_task
from .channel import ChannelMention, Channel
from typing import ForwardRef, TYPE_CHECKING
from .sticker import Sticker, StickerItem
from src.discord.types import Snowflake
from .role import RoleSubscriptionData
from .application import Application
from .attachment import Attachment
from .component import Component
from .reaction import Reaction
from .base import RawBaseModel
from datetime import datetime
from pydantic import Field
from .guild import Guild
from .embed import Embed
from orjson import dumps
from .user import User
from .poll import Poll


ResolvedRef = ForwardRef('Resolved')


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


class AllowedMentions(RawBaseModel):
    parse: list[AllowedMentionType] = Field(default_factory=list)
    roles: list[Snowflake] | None = None
    users: list[Snowflake] | None = None
    replied_user: bool | None = None


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
    flags: MessageFlag
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
    if TYPE_CHECKING:
        from .resolved import Resolved
        resolved: Resolved
    else:
        resolved: ResolvedRef | None = None
    poll: Poll | None = None
    call: MessageCall | None = None
    # ? library only, not sent by discord
    channel: Channel | None = None
    guild: Guild | None = None

    @property
    def jump_url(self) -> str:
        if self.guild is None:
            return f'https://discord.com/channels/@me/{self.channel_id}/{self.id}'

        return f'https://discord.com/channels/{self.guild.id}/{self.channel_id}/{self.id}'

    async def populate(self) -> None:
        await super().populate()
        if self.channel_id is None:
            return

        self.channel = await Channel.fetch(self.channel_id)

        if self.channel.guild_id is None:
            return

        self.guild = await Guild.fetch(self.channel.guild_id)

    async def delete(
        self,
        reason: str | None = None
    ) -> tuple[int, dict] | None:
        return await request(
            Route(
                'DELETE',
                '/channels/{channel_id}/messages/{message_id}',
                channel_id=self.channel_id,
                message_id=self.id
            ),
            reason=reason
        )

    @classmethod
    async def fetch(
        cls,
        channel_id: Snowflake,
        message_id: Snowflake
    ) -> Message:
        return cls(
            **await request(
                Route(
                    'GET',
                    '/channels/{channel_id}/messages/{message_id}',
                    channel_id=channel_id,
                    message_id=message_id
                )
            )
        )

    @classmethod
    async def send(
        cls,
        channel_id: Snowflake,
        content: str | None = None,
        *,
        tts: bool = False,
        embeds: list[Embed] | None = None,
        attachments: list[File] | None = None,
        components: list[Component] | None = None,
        sticker_ids: list[Snowflake] | None = None,
        reference: Message | MessageReference | None = None,
        allowed_mentions: AllowedMentions | None = None,
        delete_after: float | None = None,
    ) -> Message:
        json = {}

        if content is not None:
            json['content'] = content

        if tts:
            json['tts'] = tts

        if embeds:
            json['embed'] = [embed.model_dump(mode='json') for embed in embeds]

        if components:
            json['components'] = [component.model_dump(
                mode='json') for component in components]

        if sticker_ids:
            json['sticker_ids'] = sticker_ids

        if reference:
            if isinstance(reference, Message):
                json['message_reference'] = MessageReference(
                    type=MessageReferenceType.DEFAULT,
                    message_id=reference.id,
                    channel_id=reference.channel_id
                ).model_dump(mode='json')
            else:
                json['message_reference'] = reference.model_dump(mode='json')

        if allowed_mentions:
            json['allowed_mentions'] = allowed_mentions.model_dump(mode='json')

        form = None  # ? mypy is stupid
        if attachments:
            form, json_attachments = [], []
            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload_dict(index))
                form.append(attachment.as_form_dict(index))

            json['attachments'] = json_attachments
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        route = Route(
            'POST',
            '/channels/{channel_id}/messages',
            channel_id=channel_id
        )

        self = (
            cls(
                **await request(
                    route,
                    form=form,
                    files=attachments
                )
            )
            if attachments else
            cls(
                **await request(
                    route,
                    json=json
                )
            )
        )

        if delete_after:
            get_event_loop().call_later(
                delete_after,
                create_task,
                self.delete()
            )

        return self

    async def edit(
        self,
        content: str | None = None,
        *,
        embeds: list[Embed] | None = None,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        allowed_mentions: AllowedMentions | None = None,
    ) -> Message:
        json = {}

        if content is not None:
            json['content'] = content

        if embeds:
            json['embed'] = [embed.model_dump(mode='json') for embed in embeds]

        if components:
            json['components'] = [component.model_dump(
                mode='json') for component in components]

        if allowed_mentions:
            json['allowed_mentions'] = allowed_mentions.model_dump(mode='json')

        form = None
        if attachments:
            form, json_attachments = [], []
            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload_dict(index))
                form.append(attachment.as_form_dict(index))

            json['attachments'] = json_attachments
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        return (
            self.__class__(
                **await request(
                    Route(
                        'PATCH',
                        '/channels/{channel_id}/messages/{message_id}',
                        channel_id=self.channel_id,
                        message_id=self.id
                    ),
                    form=form,
                    files=attachments
                )
            )
            if attachments else
            self.__class__(
                **await request(
                    Route(
                        'PATCH',
                        '/channels/{channel_id}/messages/{message_id}',
                        channel_id=self.channel_id,
                        message_id=self.id
                    ),
                    json=json
                )
            )
        )
