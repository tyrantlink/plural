from .models import Modal, InteractionCallback, ActionRow, TextInput, Button, ButtonStyle
from typing import Callable


components: dict[str, Modal | Button] = {}


def modal(
    custom_id: str,
    title: str | None = None,
    text_inputs: list[TextInput] | None = None,
    extra: list[str] | None = None
) -> Callable[[InteractionCallback], Modal]:
    text_inputs = text_inputs or []
    def decorator(callback: InteractionCallback) -> Modal:
        modal = Modal(
            title=title,
            custom_id=custom_id,
            components=[ActionRow(components=text_inputs)],
            callback=callback,
            extra=extra
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
