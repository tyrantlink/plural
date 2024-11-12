from __future__ import annotations
from src.discord.models.base import PydanticArbitraryType
from .enums import MessageFlag, InteractionCallbackType
from src.discord.http import File, Route, request
from .message import Message, AllowedMentions
from src.db import UserProxyInteraction
from .component import Component
from typing import TYPE_CHECKING
from src.models import project
from .webhook import Webhook
from asyncio import gather
from .modal import Modal
from .embed import Embed
from orjson import dumps
from .poll import Poll


if TYPE_CHECKING:
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
        flags: MessageFlag | None = MessageFlag.EPHEMERAL,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        poll: Poll | None = None,
    ) -> Message:
        webhook = Webhook.from_interaction(self.interaction)

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

    async def ack(self) -> None:
        """only for MESSAGE_COMPONENT and MODAL interactions"""

        await request(
            self.callback_route,
            json={
                'type': InteractionCallbackType.DEFERRED_UPDATE_MESSAGE.value
            }
        )

    async def send_message(
        self,
        content: str | None = None,
        *,
        tts: bool = False,
        embeds: list[Embed] | None = None,
        allowed_mentions: AllowedMentions | None = None,
        flags: MessageFlag | None = MessageFlag.EPHEMERAL,
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
            json['components'] = [component.model_dump(
                mode='json') for component in components]

        if poll:
            json['poll'] = poll.model_dump(mode='json')

        if flags:
            json['flags'] = flags.value

        form = None  # ? mypy is stupid
        if attachments:
            form, json_attachments = [], []
            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload_dict(index))
                form.append(attachment.as_form_dict(index))

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

        message = Message(
            **(
                await request(
                    self.callback_route,
                    **request_args
                )
            )['resource']['message']
        )

        if self.userproxy:
            await UserProxyInteraction(
                message_id=message.id,
                token=self.interaction.token
            ).save()

        return message

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

    async def edit_message(
        self,
        message_id: int,
        content: str | None = None,
        *,
        embeds: list[Embed] | None = None,
        components: list[Component] | None = None,
        attachments: list[File] | None = None,
        allowed_mentions: AllowedMentions | None = None,
    ) -> Message | None:
        interaction = await UserProxyInteraction.find_one({
            'message_id': message_id
        })

        if interaction is None:
            await self.send_message(
                'message not found\ndue to discord limitations, you can\'t edit messages that are older than 15 minutes',
            )
            return None

        webhook = Webhook.from_proxy_interaction(
            interaction,
            self.interaction.application_id
        )

        message, *_ = await gather(
            webhook.edit_message(
                message_id,
                content=content,
                embeds=embeds,
                components=components,
                attachments=attachments,
                allowed_mentions=allowed_mentions
            ),
            self.ack()
        )

        return message

    #! make update_message for message components