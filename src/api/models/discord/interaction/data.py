from __future__ import annotations
from ..component import TextInput, ActionRow, Component
from pydantic import BaseModel, model_validator
from ..enums import CommandType, OptionType
from ..attachment import Attachment
from ..resolved import ResolvedData
from typing import TYPE_CHECKING
from ..option import Option


if TYPE_CHECKING:
    class InteractionData(BaseModel):
        id: str
        name: str
        type: CommandType
        resolved: ResolvedData
        options: list[Option]
        guild_id: str
        target_id: str
        custom_id: str
        components: list[ActionRow]

    class CommandInteractionData(BaseModel):
        id: str
        name: str
        type: CommandType
        resolved: ResolvedData | None = None
        options: list[Option] | None = None
        guild_id: str | None = None
        target_id: str | None = None

    class ModalInteractionData(BaseModel):
        custom_id: str
        components: list[ActionRow[TextInput]]

else:
    class InteractionData(BaseModel):
        id: str | None = None
        name: str | None = None
        type: CommandType | None = None
        resolved: ResolvedData | None = None
        options: list[Option] | None = None
        guild_id: str | None = None
        target_id: str | None = None
        custom_id: str | None = None
        components: list[Component] | None = None

        @model_validator(mode='before')
        def parse_attachments(cls, values):
            resolved_attachments = values.get(
                'resolved', {}).get('attachments', {})

            if not resolved_attachments:
                return values

            for option in values.get('options', []):
                if (
                    option['type'] != OptionType.ATTACHMENT.value or
                    option['value'] not in resolved_attachments
                ):
                    continue

                option['value'] = Attachment.model_validate(
                    resolved_attachments[option['value']]
                )
            return values

    class CommandInteractionData(InteractionData):
        ...

    class ModalInteractionData(InteractionData):
        ...
