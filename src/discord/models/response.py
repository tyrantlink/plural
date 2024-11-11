from __future__ import annotations
from .enums import MessageFlag, InteractionCallbackType, InteractionType
from pydantic_core.core_schema import CoreSchema, none_schema
from pydantic.json_schema import JsonSchemaValue
from src.discord.http import BASE_URL, File
from typing import TYPE_CHECKING, Literal
from src.core.session import session
from .message import AllowedMentions
from .component import Component
from src.models import project
from .embed import Embed
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
        self.http_allowed = interaction.application_id == project.application_id

    async def defer(self, flags: MessageFlag | Literal[0] = MessageFlag.EPHEMERAL) -> None:
        await session.post(
            f'{BASE_URL}/interactions/{self.interaction.id}/{self.interaction.token}/callback',
            json={
                'type': InteractionCallbackType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
                'data': {
                    'flags': flags
                }
            }
        )

    async def ack(self) -> None:
        """only for MESSAGE_COMPONENT interactions"""

        assert self.interaction.type == InteractionType.MESSAGE_COMPONENT

        await session.post(
            f'{BASE_URL}/interactions/{self.interaction.id}/{self.interaction.token}/callback',
            json={
                'type': InteractionCallbackType.DEFERRED_UPDATE_MESSAGE
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
    ) -> None:
        await session.post(
            f'{BASE_URL}/interactions/{self.interaction.id}/{self.interaction.token}/callback',
            json={
                'type': InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE,
                'data': {
                    'content': content,
                }
            }
        )
