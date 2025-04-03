from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from orjson import dumps

from plural.missing import is_not_missing, MISSING

from src.discord.enums import WebhookType, MessageFlag, InteractionContextType
from src.discord.models.base import RawBaseModel
from src.core.http import request, Route

from .message import Message, AllowedMentions


if TYPE_CHECKING:
    from plural.db import Message as DBMessage
    from plural.missing import Optional, Nullable

    from src.discord.types import Snowflake
    from src.core.http import File

    from .component import MessageComponent
    from .interaction import Interaction
    from .channel import Channel
    from .embed import Embed
    from .guild import Guild
    from .poll import Poll
    from .user import User


__all__ = (
    'Webhook',
)


class Webhook(RawBaseModel):
    id: Snowflake
    """the id of the webhook"""
    type: WebhookType
    """the type of the webhook"""
    guild_id: Optional[Nullable[Snowflake]]
    """the guild id this webhook is for, if any"""
    channel_id: Nullable[Snowflake]
    """the channel id this webhook is for, if any"""
    user: Optional[User]
    """the user this webhook was created by (not returned when getting a webhook with its token)"""
    name: Nullable[str]
    """the default name of the webhook"""
    avatar: Nullable[str]
    """the default user avatar hash of the webhook"""
    token: Optional[str]
    """the secure token of the webhook (returned for Incoming Webhooks)"""
    application_id: Nullable[Snowflake]
    """the bot/OAuth2 application that created this webhook"""
    source_guild: Optional[Guild]
    """the guild of the channel that this webhook is following (returned for Channel Follower Webhooks)"""
    source_channel: Optional[Channel]
    """the channel that this webhook is following (returned for Channel Follower Webhooks)"""
    url: Optional[str]
    """the url used for executing the webhook (returned by the webhooks OAuth2 flow)"""

    @classmethod
    def from_interaction(
        cls,
        interaction: Interaction,
    ) -> Webhook:
        return cls(
            id=interaction.application_id,
            type=WebhookType.APPLICATION,
            channel_id=None,
            name=None,
            avatar=None,
            token=interaction.token,
            application_id=None
        )

    @classmethod
    def from_db_message(
        cls,
        message: DBMessage,
    ) -> Webhook:
        return cls(
            id=message.bot_id,
            type=WebhookType.APPLICATION,
            channel_id=message.channel_id,
            token=message.interaction_token,
            name=None,
            avatar=None,
            application_id=None
        )

    async def fetch_message(
        self,
        message_id: int | Literal['@original'],
        thread_id: int | None = None
    ) -> Message:
        from .message import Message

        params = (
            {'thread_id': str(thread_id)}
            if thread_id is not None
            else {}
        )

        return Message(**await request(
            Route(
                'GET',
                '/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}',
                webhook_id=self.id,
                webhook_token=self.token,
                message_id=message_id),
            **params
        ))

    async def execute(
        self,
        content: Optional[Nullable[str]] = None,
        *,
        tts: Optional[bool] = MISSING,
        embeds: Optional[Nullable[list[Embed]]] = MISSING,
        allowed_mentions: Optional[Nullable[AllowedMentions]] = MISSING,
        flags: Optional[Nullable[MessageFlag]] = MessageFlag.EPHEMERAL,
        components: Optional[Nullable[list[MessageComponent]]] = MISSING,
        attachments: Optional[Nullable[list[File]]] = MISSING,
        poll: Optional[Nullable[Poll]] = MISSING,
        with_response: bool = False
    ) -> Message | None:
        json, form = {}, None

        if is_not_missing(content):
            json['content'] = content

        if is_not_missing(tts):
            json['tts'] = tts

        if is_not_missing(embeds):
            json['embeds'] = [
                embed.as_payload()
                for embed in embeds or []
            ]

        if is_not_missing(allowed_mentions):
            json['allowed_mentions'] = (
                allowed_mentions.as_payload()
                if allowed_mentions is not None
                else {}
            )

        if isinstance(flags, type(MISSING)):
            flags = (
                MessageFlag.NONE
                if self.interaction.context == InteractionContextType.BOT_DM else
                MessageFlag.EPHEMERAL
            )

        json['flags'] = (
            flags.value
            if flags
            else flags
        )

        if is_not_missing(components):
            json['components'] = [
                component.as_payload()
                for component in components or []
            ]

        if is_not_missing(poll):
            json['poll'] = (
                poll.as_payload()
                if poll is not None
                else {}
            )

        if attachments:
            form, json_attachments = [], []

            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload(index))
                form.append(attachment.as_form_dict(index))

                if attachment.is_voice_message:
                    json['flags'] = (
                        json.get('flags', 0) | MessageFlag.IS_VOICE_MESSAGE
                    )

            json['attachments'] = json_attachments

        if form:
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        request_args = ({
            'params': {
                'wait': 'true'
            }}
            if with_response else
            {}
        )

        request_args.update(
            {
                'form': form,
                'files': attachments
            }
            if attachments else
            {
                'json': json
            }
        )

        message = await request(Route(
            'POST',
            '/webhooks/{webhook_id}/{webhook_token}',
            webhook_id=self.id,
            webhook_token=self.token
        ), **request_args)

        return Message(**message)

    async def edit_message(
        self,
        message_id: Snowflake | Literal['@original'],
        content: Optional[Nullable[str]] = None,
        *,
        embeds: Optional[Nullable[list[Embed]]] = MISSING,
        allowed_mentions: Optional[Nullable[AllowedMentions]] = MISSING,
        components: Optional[Nullable[list[MessageComponent]]] = MISSING,
        attachments: Optional[Nullable[list[File]]] = MISSING,
        poll: Optional[Nullable[Poll]] = MISSING,
        thread_id: Optional[Snowflake] = MISSING
    ) -> Message | None:
        json, form = {}, None

        if is_not_missing(content):
            json['content'] = content

        if is_not_missing(embeds):
            json['embeds'] = [
                embed.as_payload()
                for embed in embeds or []
            ]

        if is_not_missing(allowed_mentions):
            json['allowed_mentions'] = (
                allowed_mentions.as_payload()
                if allowed_mentions is not None
                else {}
            )

        if is_not_missing(components):
            json['components'] = [
                component.as_payload()
                for component in components or []
            ]

        if is_not_missing(poll):
            json['poll'] = (
                poll.as_payload()
                if poll is not None
                else {}
            )

        if attachments:
            form, json_attachments = [], []

            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload(index))
                form.append(attachment.as_form_dict(index))

                if attachment.is_voice_message:
                    json['flags'] = (
                        json.get('flags', 0) | MessageFlag.IS_VOICE_MESSAGE
                    )

            json['attachments'] = json_attachments

        if form:
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        request_args = (
            {'params': {'thread_id': thread_id}}
            if is_not_missing(thread_id)
            else {}
        )

        request_args.update(
            {
                'form': form,
                'files': attachments
            }
            if attachments else
            {
                'json': json
            }
        )

        message = await request(Route(
            'PATCH',
            '/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}',
            webhook_id=self.id,
            webhook_token=self.token,
            message_id=message_id
        ), **request_args)

        return Message(**message)
