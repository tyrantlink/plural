from __future__ import annotations
from .enums import MessageType, MessageReferenceType, MessageFlag, AllowedMentionType, InteractionType, ApplicationIntegrationType
from src.discord.http import Route, request, File
from src.errors import HTTPException, Forbidden
from asyncio import get_event_loop, create_task
from .channel import ChannelMention, Channel
from typing import ForwardRef, TYPE_CHECKING
from src.db import DiscordCache, CacheType
from .sticker import Sticker, StickerItem  # noqa: TC001
from src.discord.types import Snowflake
from .role import RoleSubscriptionData  # noqa: TC001
from .application import Application  # noqa: TC001
from .attachment import Attachment  # noqa: TC001
from .component import Component  # noqa: TC001
from src.models import project
from .reaction import Reaction  # noqa: TC001
from .base import RawBaseModel
from pydantic import Field
from regex import finditer
from .embed import Embed  # noqa: TC001
from .guild import Guild
from orjson import dumps
from .user import User  # noqa: TC001
from .poll import Poll  # noqa: TC001

if TYPE_CHECKING:
    from datetime import datetime


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
    id: Snowflake
    type: InteractionType
    user: User
    authorizing_integration_owners: dict[
        ApplicationIntegrationType, Snowflake]
    original_response_message_id: Snowflake | None = None
    target_user: User | None = None
    target_message_id: Snowflake | None = None


class MessageInteraction(RawBaseModel):
    ...  # deprecated


class MessageCall(RawBaseModel):
    participants: list[Snowflake]
    ended_timestamp: datetime | None = None


class AllowedMentions(RawBaseModel):
    parse: list[AllowedMentionType] = Field(default_factory=list)
    roles: set[Snowflake] | None = None
    users: set[Snowflake] | None = None
    replied_user: bool | None = None

    @classmethod
    def parse_content(cls, content: str, replied_user: bool = True) -> AllowedMentions:
        return cls(
            parse=[AllowedMentionType.EVERYONE],
            roles={Snowflake(match.group(1))
                   for match in finditer(r'<@&(\d+)>', content)},
            users={Snowflake(match.group(1))
                   for match in finditer(r'<@!?(\d+)>', content)},
            replied_user=replied_user
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
    # ? i don't care enough to model partial messages right now
    message_snapshots: list[dict[str, dict]] | None = None
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

        try:
            self.channel = await Channel.fetch(self.channel_id)
        except Forbidden:
            return

        if self.channel.guild_id is None:
            return

        self.guild = await Guild.fetch(self.channel.guild_id)

    async def delete(
        self,
        reason: str | None = None,
        token: str | None = project.bot_token
    ) -> tuple[int, dict] | None:
        cached = await DiscordCache.get(self.id, None)

        if cached is not None and cached.deleted:
            return None

        return await request(
            Route(
                'DELETE',
                '/channels/{channel_id}/messages/{message_id}',
                channel_id=self.channel_id,
                message_id=self.id,
                token=token),
            reason=reason,
            token=token
        )

    @classmethod
    async def fetch(
        cls,
        channel_id: Snowflake | int,
        message_id: Snowflake | int,
        populate: bool = True,
        include_content: bool = False
    ) -> Message:
        if not include_content:
            cached = await DiscordCache.get(message_id, None, CacheType.MESSAGE)

            if cached is not None and not cached.deleted and not cached.error:
                message = cls(**cached.data)

                if populate:
                    await message.populate()

                return message
        try:
            data = await request(Route(
                'GET',
                '/channels/{channel_id}/messages/{message_id}',
                channel_id=channel_id,
                message_id=message_id
            ))
        except HTTPException as e:
            await DiscordCache.http4xx(
                e.status_code,
                CacheType.MESSAGE,
                message_id)
            raise

        message = cls(**data)

        await DiscordCache.add(
            CacheType.MESSAGE,
            data
        )

        if populate:
            await message.populate()

        return message

    @classmethod
    async def send(
        cls,
        channel_id: Snowflake | int,
        content: str | None = None,
        *,
        tts: bool = False,
        embeds: list[Embed] | None = None,
        attachments: list[File] | None = None,
        components: list[Component] | None = None,
        sticker_ids: list[Snowflake] | None = None,
        reference: Message | MessageReference | None = None,
        allowed_mentions: AllowedMentions | None = None,
        poll: Poll | None = None,
        flags: MessageFlag | None = None,
        delete_after: float | None = None,
        token: str | None = project.bot_token
    ) -> Message:
        json = {}

        if content is not None:
            json['content'] = content

        if tts:
            json['tts'] = tts

        if embeds:
            json['embed'] = [embed.model_dump(mode='json') for embed in embeds]

        if components:
            json['components'] = [
                component.as_payload()
                for component in components]

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

        if poll:
            json['poll'] = poll.as_create_request()

        if flags:
            json['flags'] = flags

        form = None  # ? mypy is stupid
        if attachments:
            form, json_attachments = [], []
            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload_dict(index))
                form.append(attachment.as_form_dict(index))
                if attachment.is_voice_message:
                    json['flags'] = json.get(
                        'flags', 0) | MessageFlag.IS_VOICE_MESSAGE

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
            cls(**await request(
                route,
                form=form,
                files=attachments,
                token=token))
            if attachments else
            cls(**await request(
                route,
                json=json,
                token=token
            ))
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
        token: str | None = project.bot_token
    ) -> Message:
        json = {}

        if content is not None:
            json['content'] = content

        if embeds:
            json['embed'] = [embed.model_dump(mode='json') for embed in embeds]

        if components:
            json['components'] = [
                component.as_payload()
                for component in components]

        if allowed_mentions:
            json['allowed_mentions'] = allowed_mentions.model_dump(mode='json')
        else:
            json['allowed_mentions'] = AllowedMentions(
                replied_user=(
                    self.referenced_message is not None and
                    self.referenced_message.author is not None and
                    self.referenced_message.author.id in [
                        user.id for user in self.mentions])
            ).model_dump(mode='json')

        form = None
        if attachments:
            form, json_attachments = [], []
            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload_dict(index))
                form.append(attachment.as_form_dict(index))
                if attachment.is_voice_message:
                    json['flags'] = json.get(
                        'flags', 0) | MessageFlag.IS_VOICE_MESSAGE

            json['attachments'] = json_attachments
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        return (
            self.__class__(**await request(
                Route(
                    'PATCH',
                    '/channels/{channel_id}/messages/{message_id}',
                    channel_id=self.channel_id,
                    message_id=self.id),
                form=form,
                files=attachments,
                token=token))
            if attachments else
            self.__class__(**await request(
                Route(
                    'PATCH',
                    '/channels/{channel_id}/messages/{message_id}',
                    channel_id=self.channel_id,
                    message_id=self.id),
                json=json,
                token=token
            ))
        )
