from __future__ import annotations

from typing import TYPE_CHECKING

from .enums import ComponentType
from .models import (
    InteractionCallback,
    SelectMenu,
    ActionRow,
    TextInput,
    Button,
    Modal
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .enums import ButtonStyle


components: dict[str, Modal | Button | SelectMenu] = {}


def modal(
    custom_id: str,
    title: str,
    text_inputs: list[TextInput]
) -> Callable[[InteractionCallback], Modal]:
    def decorator(callback: InteractionCallback) -> Modal:
        modal = Modal(
            title=title,
            custom_id=custom_id,
            components=[
                ActionRow(components=[text_input])
                for text_input in text_inputs],
            callback=callback
        )

        if custom_id in components:
            raise ValueError(f'component {custom_id} already exists')

        components.update({custom_id: modal})

        return modal
    return decorator


def button(
    custom_id: str,
    label: str,
    style: ButtonStyle
) -> Callable[[InteractionCallback], Button]:
    def decorator(callback: InteractionCallback) -> Button:
        button = Button(
            custom_id=custom_id,
            label=label,
            style=style,
            callback=callback
        )

        if custom_id in components:
            raise ValueError(f'component {custom_id} already exists')

        components.update({custom_id: button})

        return button
    return decorator


def string_select(
    custom_id: str,
    options: list[SelectMenu.Option],
    placeholder: str,
    min_values: int = 1,
    max_values: int = 1
) -> Callable[[InteractionCallback], SelectMenu]:
    def decorator(callback: InteractionCallback) -> SelectMenu:
        select = SelectMenu(
            type=ComponentType.STRING_SELECT,
            custom_id=custom_id,
            options=options,
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            callback=callback
        )

        if custom_id in components:
            raise ValueError(f'component {custom_id} already exists')

        components.update({custom_id: select})

        return select
    return decorator
