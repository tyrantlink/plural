from __future__ import annotations
from .base import RawBaseModel, PydanticArbitraryType
from typing import TYPE_CHECKING, Annotated, Any
from .component import ActionRow, TextInput

if TYPE_CHECKING:
    from .interaction import InteractionCallback


class Modal(RawBaseModel, PydanticArbitraryType):
    title: str | None
    custom_id: str
    components: list[ActionRow]
    # ? library stuff
    callback: Annotated[InteractionCallback,
                        PydanticArbitraryType] | None = None
    modified: bool = False
    extra: list[str] | None = None

    def as_payload(self) -> dict:
        if self.title is None:
            raise ValueError('title is required for modal payload')

        custom_id = '.'.join([self.custom_id] + (self.extra or []))

        if len(custom_id) > 100:
            raise ValueError(
                'custom_id (with extra) must be less than 100 characters')

        return {
            'title': self.title,
            'custom_id': custom_id,
            'components': [component.as_payload() for component in self.components]
        }

    def __get_self(self) -> Modal:
        if self.modified:
            return self
        return self.model_copy(deep=True)

    def with_title(self, title: str) -> Modal:
        modal = self.__get_self()
        modal.title = title
        return modal

    def with_text_placeholder(self, index: int, placeholder: str) -> Modal:
        modal = self.__get_self()

        if not isinstance(modal.components[0].components[index], TextInput):
            raise ValueError(f'Component at index {index} is not a TextInput')

        modal.components[0].components[
            index
        ].placeholder = placeholder  # type: ignore

        return modal

    def with_text_value(self, index: int, value: str) -> Modal:
        modal = self.__get_self()

        if not isinstance(modal.components[0].components[index], TextInput):
            raise ValueError(f'Component at index {index} is not a TextInput')

        modal.components[0].components[
            index
        ].value = value  # type: ignore

        return modal

    def with_extra(self, extra: list[str]) -> Modal:
        modal = self.__get_self()
        modal.extra = extra
        return modal
