from __future__ import annotations
from .base import RawBaseModel, PydanticArbitraryType
from src.db import Member as ProxyMember, Group
from .component import ActionRow, TextInput
from typing import TYPE_CHECKING, Annotated
from .enums import ModalExtraType
from .channel import Channel
from .user import User

if TYPE_CHECKING:
    from .interaction import InteractionCallback

# ? i'm so good at names
ModalExtraTypeType = None | str | int | bool | User | Channel | ProxyMember | Group


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

    def with_extra(
        self,
        *extra: ModalExtraTypeType
    ) -> Modal:
        modal = self.__get_self()
        modal.extra = modal.extra or []

        for value in extra:
            parsed = ''
            match value:
                case None:
                    parsed = str(ModalExtraType.NONE)
                case str():
                    parsed = f'{ModalExtraType.STRING}{value}'
                case bool():
                    parsed = f'{ModalExtraType.BOOLEAN}{int(value)}'
                case int():
                    parsed = f'{ModalExtraType.INTEGER}{value}'
                case User():
                    parsed = f'{ModalExtraType.USER}{value.id}'
                case Channel():
                    parsed = f'{ModalExtraType.CHANNEL}{value.id}'
                case ProxyMember():
                    parsed = f'{ModalExtraType.MEMBER}{value.id}'
                case Group():
                    parsed = f'{ModalExtraType.GROUP}{value.id}'
                case _:
                    raise ValueError(f'invalid extra type `{type(value)}`')

            modal.extra.append(parsed)

        if len('.'.join([modal.custom_id] + (modal.extra))) > 100:
            raise ValueError(
                'custom_id (with extra) must be less than 100 characters'
            )

        return modal
