from .models import Modal, InteractionCallback, ActionRow, TextInput
from typing import Callable


components: dict[str, Modal] = {}


def modal(
    custom_id: str,
    title: str | None = None,
    text_inputs: list[TextInput] = [],
    extra: list[str] | None = None
) -> Callable[[InteractionCallback], Modal]:
    def decorator(callback: InteractionCallback) -> Modal:
        modal = Modal(
            title=title,
            custom_id=custom_id,
            components=[ActionRow(components=text_inputs)],
            callback=callback,
            extra=extra
        )

        components.update({custom_id: modal})

        return modal
    return decorator
