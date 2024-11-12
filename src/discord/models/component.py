from __future__ import annotations
from .enums import ComponentType, TextInputStyle
from .base import RawBaseModel
from typing import Sequence


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


Component = TextInput | ActionRow
