from __future__ import annotations
from .enums import MessageFlag, InteractionCallbackType, InteractionContextType
from src.discord.models.base import PydanticArbitraryType
from src.models import project, MISSING, MissingNoneOr
from src.discord.http import File, Route, request
from .message import Message, AllowedMentions
from .component import Component
from typing import TYPE_CHECKING
from .webhook import Webhook
from .modal import Modal
from .embed import Embed
from orjson import dumps
from .poll import Poll


if TYPE_CHECKING:
    from .application_command import ApplicationCommandOptionChoice
    from .interaction import Interaction


class InteractionFollowup(PydanticArbitraryType):
    def __init__(self, interaction: Interaction) -> None:
        # ? created empty in model_validator, created properly in Interaction.populate()
        self.interaction = interaction
        self.userproxy = interaction.application_id != project.application_id
        self.bot_token = (
            None  # ! implement userproxy tokens here
            if self.userproxy else
            project.bot_token
        )

    async def send(
        self,
        content: str | None = None,
        *,
        tts: bool = False,
        embeds: list[Embed] | None = None,
        allowed_mentions: AllowedMentions | None = None,
        flags: MissingNoneOr[MessageFlag] = MISSING,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        poll: Poll | None = None,
    ) -> Message:
        webhook = Webhook.from_interaction(self.interaction)

        if flags is MISSING:
            flags = (
                MessageFlag.NONE
                if self.interaction.context == InteractionContextType.BOT_DM
                else MessageFlag.EPHEMERAL
            )

        if not flags:
            flags = MessageFlag.EPHEMERAL

        return await webhook.execute(
            content=content,
            wait=True,
            tts=tts,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            components=components,
            attachments=attachments,
            flags=flags,
            poll=poll
        )

    async def edit_message(
        self,
        message_id: int,
        content: str | None = None,
        *,
        embeds: list[Embed] | None = None,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        allowed_mentions: AllowedMentions | None = None,
    ) -> Message:
        webhook = Webhook.from_interaction(self.interaction)

        return await webhook.edit_message(
            message_id,
            content=content,
            embeds=embeds,
            components=components,
            attachments=attachments,
            allowed_mentions=allowed_mentions
        )


class InteractionResponse(PydanticArbitraryType):
    def __init__(self, interaction: Interaction) -> None:
        # ? created empty in model_validator, created properly in Interaction.populate()
        self.interaction = interaction
        self.responded = False
        self.userproxy = interaction.application_id != project.application_id
        self.bot_token = (
            None  # ! implement userproxy tokens here
            if self.userproxy else
            project.bot_token
        )

    @property
    def callback_route(self) -> Route:
        return Route(
            'POST',
            '/interactions/{interaction_id}/{interaction_token}/callback',
            interaction_id=self.interaction.id,
            interaction_token=self.interaction.token
        )

    async def defer(self, flags: MessageFlag = MessageFlag.EPHEMERAL) -> None:
        await request(
            self.callback_route,
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

        await request(
            self.callback_route,
            json={
                'type': InteractionCallbackType.DEFERRED_UPDATE_MESSAGE.value
            }
        )
        self.responded = True

    async def send_message(
        self,
        content: str | None = None,
        *,
        tts: bool = False,
        embeds: list[Embed] | None = None,
        allowed_mentions: AllowedMentions | None = None,
        flags: MissingNoneOr[MessageFlag] = MISSING,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        poll: Poll | None = None,
    ) -> Message:
        json = {}

        if content is not None:
            json['content'] = content

        if tts:
            json['tts'] = tts

        if embeds:
            json['embeds'] = [embed.model_dump(
                mode='json') for embed in embeds]

        if allowed_mentions:
            json['allowed_mentions'] = allowed_mentions.model_dump(mode='json')

        if components:
            json['components'] = [
                component.as_payload()
                for component in components]

        if poll:
            json['poll'] = poll.model_dump(mode='json')

        if flags is MISSING:
            flags = (
                MessageFlag.NONE
                if self.interaction.context == InteractionContextType.BOT_DM
                else MessageFlag.EPHEMERAL
            )

        if flags:
            json['flags'] = flags.value

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

        json = {
            'type': InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE.value,
            'data': json
        }

        if form:
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        request_args = {
            'token': None,
            'params': {
                'with_response': 'true'
            }
        }

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

        message = (
            await request(
                self.callback_route,
                **request_args
            )
        )['resource']['message']
        self.responded = True

        return Message(**message)

    async def send_modal(
        self,
        modal: Modal
    ) -> None:
        json = {
            'type': InteractionCallbackType.MODAL.value,
            'data': modal.as_payload()
        }

        await request(
            self.callback_route,
            json=json
        )
        self.responded = True

    async def edit_message(
        self,
        content: str | None = None,
        *,
        embeds: list[Embed] | None = None,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        allowed_mentions: AllowedMentions | None = None,
    ) -> Message | None:
        await Webhook.from_interaction(self.interaction).edit_message(
            '@original',
            content=content,
            embeds=embeds,
            components=components,
            attachments=attachments,
            allowed_mentions=allowed_mentions
        )
        self.responded = True

    async def update_message(
        self,
        content: str | None = None,
        *,
        embeds: list[Embed] | None = None,
        components: list[Component] | None = None
    ) -> Message | None:
        """only for MESSAGE_COMPONENT interactions"""
        json = {}

        if content is not None:
            json['content'] = content

        if embeds:
            json['embeds'] = [
                embed.model_dump(
                    mode='json') for embed in embeds]

        if components:
            json['components'] = [
                component.as_payload()
                for component in components]

        await request(
            self.callback_route,
            json={
                'type': InteractionCallbackType.UPDATE_MESSAGE.value,
                'data': json
            }
        )

    async def send_autocomplete_result(
        self,
        choices: list[ApplicationCommandOptionChoice],
    ) -> None:
        await request(
            self.callback_route,
            json={
                'type': InteractionCallbackType.APPLICATION_COMMAND_AUTOCOMPLETE_RESULT.value,
                'data': {
                    'choices': [
                        choice.model_dump(mode='json')
                        for choice in
                        choices
                    ]
                }
            }
        )
        self.responded = True
