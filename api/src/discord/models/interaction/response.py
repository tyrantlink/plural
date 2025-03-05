from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from orjson import dumps

from plural.missing import MISSING, Optional, Nullable, is_not_missing
from plural.errors import HTTPException, InteractionError

from src.core.http import request, Route, File

from src.discord.models.base import PydanticArbitraryType

from src.discord.models.message import Message, AllowedMentions
from src.discord.models.webhook import Webhook
from src.discord.models.poll import Poll
from src.discord.enums import (
    InteractionCallbackType,
    InteractionContextType,
    InteractionType,
    MessageFlag
)


if TYPE_CHECKING:
    from . import Interaction

    from src.discord.types import Snowflake
    from src.discord.models import (
        ApplicationCommand,
        MessageComponent,
        Embed,
        Modal
    )


class InteractionResponse(PydanticArbitraryType):
    def __init__(self, interaction: Interaction) -> None:
        self.interaction = interaction
        self.responded = False

    @property
    def callback(self) -> Route:
        return Route(
            'POST',
            '/interactions/{interaction_id}/{interaction_token}/callback',
            interaction_id=self.interaction.id,
            interaction_token=self.interaction.token
        )

    async def defer(self, flags: MessageFlag = MessageFlag.EPHEMERAL) -> None:
        await request(
            self.callback,
            json={
                'type': InteractionCallbackType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE.value,
                'data': {
                    'flags': flags
                }
            }
        )

        self.responded = True

    async def ack(self) -> None:
        """only for MESSAGE_COMPONENT and MODAL interactions"""

        if self.interaction.type not in (
            InteractionType.MESSAGE_COMPONENT,
            InteractionType.MODAL_SUBMIT
        ):
            raise ValueError(
                'ack is only for MESSAGE_COMPONENT and MODAL interactions'
            )

        await request(
            self.callback,
            json={
                'type': InteractionCallbackType.DEFERRED_UPDATE_MESSAGE.value
            }
        )

        self.responded = True

    async def send_message(
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
            match embeds:
                case None:
                    json['embeds'] = []
                case _:
                    json['embeds'] = [
                        embed.as_payload()
                        for embed in embeds
                    ]

        if is_not_missing(allowed_mentions):
            match allowed_mentions:
                case None:
                    json['allowed_mentions'] = {}
                case _:
                    json['allowed_mentions'] = allowed_mentions.model_dump(
                        mode='json'
                    )

        if not is_not_missing(flags):
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
            match components:
                case None:
                    json['components'] = []
                case _:
                    json['components'] = [
                        component.as_payload()
                        for component in components
                    ]

        if is_not_missing(poll):
            match poll:
                case None:
                    json['poll'] = None
                case _:
                    assert isinstance(poll, Poll)
                    json['poll'] = poll.as_payload()

        if is_not_missing(attachments) and attachments is not None:
            form, json_attachments = [], []

            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload(index))
                form.append(attachment.as_form_dict(index))

                if attachment.is_voice_message:
                    json['flags'] = (
                        json.get('flags', 0) | MessageFlag.IS_VOICE_MESSAGE
                    )

            json['attachments'] = json_attachments

        json = {
            'type': InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE.value,
            'data': json
        }

        if form:
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        request_args = {'params': {
            'with_response': str(with_response).lower()
        }}

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

        self.responded = True

        try:
            response = await request(
                self.callback,
                **request_args
            )

            if not with_response:
                return None

            message = response['resource']['message']
        except HTTPException as e:
            if (
                e.status_code == 400 and
                isinstance(e.detail, dict) and
                e.detail.get('code') == 200000
            ):
                raise InteractionError('message blocked by automod') from e
            raise

        return Message(**message)

    async def send_autocomplete_result(
        self,
        choices: list[ApplicationCommand.Option.Choice]
    ) -> None:
        callback = self.callback
        callback.silent = True

        await request(
            callback,
            json={
                'type': InteractionCallbackType.APPLICATION_COMMAND_AUTOCOMPLETE_RESULT.value,
                'data': {'choices': [
                    choice.as_payload()
                    for choice in
                    choices
                ]}})
        self.responded = True

    async def update_message(
        self,
        content: Optional[Nullable[str]] = MISSING,
        *,
        embeds: Optional[Nullable[list[Embed]]] = MISSING,
        components: Optional[Nullable[list[MessageComponent]]] = MISSING,
        with_response: bool = False
    ) -> Message | None:
        """only for MESSAGE_COMPONENT interactions"""
        json = {}

        if is_not_missing(content):
            json['content'] = content

        if is_not_missing(embeds):
            json['embeds'] = [
                embed.as_payload()
                for embed in
                embeds
            ]

        if is_not_missing(components):
            json['components'] = [
                component.as_payload()
                for component in
                components
            ]

        self.responded = True

        try:
            response = await request(
                self.callback,
                json={
                    'type': InteractionCallbackType.UPDATE_MESSAGE.value,
                    'data': json},
                params={'with_response': str(with_response).lower()}
            )

            if not with_response:
                return None

            message = response['resource']['message']
        except HTTPException as e:
            if (
                e.status_code == 400 and
                isinstance(e.detail, dict) and
                e.detail.get('code') == 200000
            ):
                raise InteractionError('message blocked by automod') from e
            raise

        return Message(**message)

    async def send_modal(
        self,
        modal: Modal
    ) -> None:
        self.responded = True
        await request(
            self.callback,
            json={
                'type': InteractionCallbackType.MODAL.value,
                'data': modal.as_payload()
            }
        )


class InteractionFollowup(PydanticArbitraryType):
    def __init__(self, interaction: Interaction) -> None:
        self.interaction = interaction

    async def send(
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
        try:
            return await Webhook.from_interaction(self.interaction).execute(
                content,
                tts=tts,
                embeds=embeds,
                allowed_mentions=allowed_mentions,
                flags=flags,
                components=components,
                attachments=attachments,
                poll=poll,
                with_response=with_response
            )
        except HTTPException as e:
            if (
                e.status_code == 400 and
                isinstance(e.detail, dict) and
                e.detail.get('code') == 200000
            ):
                raise InteractionError('message blocked by automod') from e
            raise

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
    ) -> Message | None:
        try:
            return await Webhook.from_interaction(self.interaction).edit_message(
                message_id,
                content,
                embeds=embeds,
                allowed_mentions=allowed_mentions,
                components=components,
                attachments=attachments,
                poll=poll)
        except HTTPException as e:
            if (
                e.status_code == 400 and
                isinstance(e.detail, dict) and
                e.detail.get('code') == 200000
            ):
                raise InteractionError('message blocked by automod') from e
            raise
