from __future__ import annotations
from typing import Sequence, Literal, TYPE_CHECKING
from .enums import ComponentType, TextInputStyle
from pydantic import BaseModel


if TYPE_CHECKING:
    class Component(BaseModel):
        type: ComponentType

    class ActionRow(Component):
        type: Literal[ComponentType.ACTION_ROW] = ComponentType.ACTION_ROW
        components: Sequence[TextInput]

    class TextInput(Component):
        type: Literal[ComponentType.TEXT_INPUT] = ComponentType.TEXT_INPUT
        custom_id: str
        style: TextInputStyle
        label: str
        min_length: int | None = None
        max_length: int | None = None
        required: bool | None = None
        value: str | None = None
        placeholder: str | None = None

else:
    class Component(BaseModel):
        type: ComponentType
        custom_id: str | None = None
        style: TextInputStyle | None = None
        label: str | None = None
        min_length: int | None = None
        max_length: int | None = None
        required: bool | None = None
        value: str | None = None
        placeholder: str | None = None
        # ? setting as TextInput because model_dump was being stupid and i don't care
        components: list[TextInput] | None = None

    class ActionRow(Component):
        type: ComponentType = ComponentType.ACTION_ROW

    class TextInput(Component):
        type: ComponentType = ComponentType.TEXT_INPUT
