from __future__ import annotations
from .enums import MessageFlag, InteractionCallbackType, InteractionType
from pydantic_core.core_schema import CoreSchema, none_schema
from src.discord.http import BASE_URL, File, Route, request
from pydantic.json_schema import JsonSchemaValue
from .message import Message, AllowedMentions
from typing import TYPE_CHECKING, Literal
from .component import Component
from src.models import project
from .embed import Embed
from orjson import dumps
from .poll import Poll


if TYPE_CHECKING:
    from .interaction import Interaction


class InteractionResponse:
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: None,
        _handler: None
    ) -> CoreSchema:
        return none_schema()

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: None
    ) -> JsonSchemaValue:
        return {'type': 'null'}

    def __init__(self, interaction: Interaction) -> None:
        # ? created empty in model_validator, created properly in Interaction.populate()
        self.interaction = interaction
        self.bot_token = (
            project.bot_token
            if interaction.application_id == project.application_id else
            None  # ! implement userproxy tokens here
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
        """only for MESSAGE_COMPONENT interactions"""

        assert self.interaction.type == InteractionType.MESSAGE_COMPONENT

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
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        json = {
            'type': InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE.value,
            'data': json
        }

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

        return Message(
            **(
                await request(
                    self.callback_route,
                    **request_args
                )
            )['resource']['message']
        )
