from __future__ import annotations
from .enums import ComponentType, TextInputStyle, ButtonStyle
from .base import RawBaseModel, PydanticArbitraryType
from typing import TYPE_CHECKING, Annotated
from src.models import MISSING, MissingOr
from src.discord.types import Snowflake  # noqa: TC001
from collections.abc import Sequence  # noqa: TC003
from .emoji import Emoji  # noqa: TC001

if TYPE_CHECKING:
    from .interaction import InteractionCallback


class BaseComponent(RawBaseModel):
    type: ComponentType

    def as_payload(self) -> dict:
        raise NotImplementedError


class ActionRow(BaseComponent):
    type: ComponentType = ComponentType.ACTION_ROW
    components: Sequence[Component]

    def as_payload(self) -> dict:
        return {
            'type': self.type.value,
            'components': [component.as_payload() for component in self.components]
        }


class Button(BaseComponent):
    type: ComponentType = ComponentType.BUTTON
    style: ButtonStyle
    label: MissingOr[str] = MISSING
    emoji: MissingOr[Emoji] = MISSING
    custom_id: MissingOr[str] = MISSING
    sku_id: MissingOr[Snowflake] = MISSING
    url: MissingOr[str] = MISSING
    disabled: MissingOr[bool] = MISSING
    # ? library stuff
    callback: Annotated[InteractionCallback,
                        PydanticArbitraryType] | None = None

    def as_payload(self) -> dict:
        json: dict = {
            'type': self.type.value,
            'style': self.style.value
        }

        if self.label:
            json['label'] = self.label

        if self.emoji:
            json['emoji'] = self.emoji.model_dump()

        if self.custom_id:
            json['custom_id'] = self.custom_id

        if self.sku_id:
            json['sku_id'] = self.sku_id

        if self.url:
            json['url'] = self.url

        if self.disabled:
            json['disabled'] = self.disabled

        return json


class TextInput(BaseComponent):
    type: ComponentType = ComponentType.TEXT_INPUT
    custom_id: str
    style: TextInputStyle | None = None
    label: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    required: bool | None = None
    value: str | None = None
    placeholder: str | None = None

    def as_payload(self) -> dict:
        if self.style is None or self.label is None:
            raise ValueError(
                'style and label are required for text input payload')

        json = {
            'type': self.type.value,
            'custom_id': self.custom_id,
            'style': self.style.value,
            'label': self.label
        }

        if self.min_length is not None:
            json['min_length'] = self.min_length

        if self.max_length is not None:
            json['max_length'] = self.max_length

        if self.required is not None:
            json['required'] = self.required

        if self.value is not None:
            json['value'] = self.value

        if self.placeholder is not None:
            json['placeholder'] = self.placeholder

        return json


Component = TextInput | Button | ActionRow
