from __future__ import annotations
from typing import TYPE_CHECKING, overload, Literal
from src.discord.http import Route, request, File
from src.discord.types import Snowflake
from src.db import UserProxyInteraction
from .enums import WebhookType
from .base import RawBaseModel
from .channel import Channel
from .guild import Guild
from orjson import dumps
from regex import search
from .user import User

if TYPE_CHECKING:
    from .message import Message, AllowedMentions
    from .interaction import Interaction
    from .component import Component
    from .embed import Embed
    from .poll import Poll


class Webhook(RawBaseModel):
    id: Snowflake
    type: WebhookType
    guild_id: Snowflake | None = None
    channel_id: Snowflake | None = None
    user: User | None = None
    name: str | None = None
    avatar: str | None = None
    token: str | None = None
    application_id: Snowflake | None = None
    source_guild: Guild | None = None
    source_channel: Channel | None = None
    url: str | None = None

    @classmethod
    async def from_url(
        cls,
        url: str
    ) -> Webhook:
        match = search(
            r"discord(?:app)?.com/api/webhooks/(?P<id>\d{17,20})/(?P<token>[\w\.\-_]{60,68})",
            url,
        )

        if match is None:
            raise ValueError("Invalid webhook URL given.")

        return cls(
            **await request(
                Route(
                    'GET',
                    '/webhooks/{webhook_id}/{webhook_token}',
                    webhook_id=match['id'],
                    webhook_token=match['token']
                )
            )
        )

    @classmethod
    def from_interaction(
        cls,
        interaction: Interaction
    ) -> Webhook:
        return cls(
            id=interaction.application_id,
            type=WebhookType.APPLICATION,
            token=interaction.token,
        )

    @classmethod
    def from_proxy_interaction(
        cls,
        interaction: UserProxyInteraction
    ) -> Webhook:
        return cls(
            id=Snowflake(interaction.application_id),
            type=WebhookType.APPLICATION,
            token=interaction.token,
        )

    @overload
    async def execute(
        self,
        content: str | None = None,
        *,
        wait: Literal[False] = False,
        thread_id: Snowflake | None = None,
        username: str | None = None,
        avatar_url: str | None = None,
        tts: bool = False,
        embeds: list[Embed] | None = None,
        allowed_mentions: AllowedMentions | None = None,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        flags: int | None = None,
        thread_name: str | None = None,
        applied_tags: list[Snowflake] | None = None,
        poll: Poll | None = None,
    ) -> None:
        ...

    @overload
    async def execute(
        self,
        content: str | None = None,
        *,
        wait: Literal[True] = True,
        thread_id: Snowflake | None = None,
        username: str | None = None,
        avatar_url: str | None = None,
        tts: bool = False,
        embeds: list[Embed] | None = None,
        allowed_mentions: AllowedMentions | None = None,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        flags: int | None = None,
        thread_name: str | None = None,
        applied_tags: list[Snowflake] | None = None,
        poll: Poll | None = None,
    ) -> Message:
        ...

    async def execute(
        self,
        content: str | None = None,
        *,
        wait: bool = False,
        thread_id: Snowflake | None = None,
        username: str | None = None,
        avatar_url: str | None = None,
        tts: bool = False,
        embeds: list[Embed] | None = None,
        allowed_mentions: AllowedMentions | None = None,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        flags: int | None = None,
        thread_name: str | None = None,
        applied_tags: list[Snowflake] | None = None,
        poll: Poll | None = None,
    ) -> Message | None:
        from .message import Message
        json = {}
        params = {}

        if content is not None:
            json['content'] = content

        if wait or self.type == WebhookType.APPLICATION:
            params['wait'] = str(wait).lower()

        if thread_id is not None:
            params['thread_id'] = thread_id

        if username is not None:
            json['username'] = username

        if avatar_url is not None:
            json['avatar_url'] = avatar_url

        if tts:
            json['tts'] = tts

        if embeds:
            json['embeds'] = [embed.model_dump(
                mode='json') for embed in embeds]

        if allowed_mentions:
            json['allowed_mentions'] = allowed_mentions.model_dump(mode='json')

        if components:
            json['components'] = [component.model_dump(
                mode='json') for component in components]

        if flags:
            json['flags'] = flags

        if thread_name:
            json['thread_name'] = thread_name

        if applied_tags:
            json['applied_tags'] = applied_tags

        if poll:
            json['poll'] = poll.as_create_request()

        route = Route(
            'POST',
            '/webhooks/{webhook_id}/{webhook_token}',
            webhook_id=self.id,
            webhook_token=self.token
        )

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

        resp = (
            await request(
                route,
                form=form,
                files=attachments
            )
            if attachments else
            await request(
                route,
                json=json,
                params=params
            )
        )

        if wait:
            return Message(**resp)

        return None

    async def edit_message(
        self,
        message_id: Snowflake | int | Literal['@original'],
        content: str | None = None,
        *,
        thread_id: Snowflake | None = None,
        embeds: list[Embed] | None = None,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        allowed_mentions: AllowedMentions | None = None,
        flags: int | None = None,
    ) -> Message:
        from .message import Message
        json = {}
        params = {}

        if content is not None:
            json['content'] = content

        if thread_id is not None:
            params['thread_id'] = thread_id

        if embeds:
            json['embeds'] = [embed.model_dump(
                mode='json') for embed in embeds]

        if components:
            json['components'] = [component.model_dump(
                mode='json') for component in components]

        if allowed_mentions:
            json['allowed_mentions'] = allowed_mentions.model_dump(mode='json')

        if flags:
            json['flags'] = flags

        route = Route(
            'PATCH',
            '/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}',
            webhook_id=self.id,
            webhook_token=self.token,
            message_id=message_id
        )

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

        return Message(
            **(
                await request(
                    route,
                    form=form,
                    files=attachments
                )
                if attachments else
                await request(
                    route,
                    json=json,
                    params=params
                )
            )
        )

    async def delete_message(
        self,
        message_id: Snowflake | int | Literal['@original'],
        thread_id: Snowflake | None = None
    ) -> None:
        await request(
            Route(
                'DELETE',
                '/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}',
                webhook_id=self.id,
                webhook_token=self.token,
                message_id=message_id
            ),
            params={'thread_id': thread_id} if thread_id else None
        )
