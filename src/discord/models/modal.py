from __future__ import annotations
from .base import RawBaseModel, PydanticArbitraryType
from .component import ActionRow, TextInput
from typing import TYPE_CHECKING, Annotated
from src.db import ProxyMember, Group
from .enums import CustomIdExtraType
from .channel import Channel
from .message import Message
from .user import User


if TYPE_CHECKING:
    from .interaction import InteractionCallback

# ? i'm so good at names
CustomIdExtraTypeType = None | str | int | bool | User | Channel | ProxyMember | Group | Message


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

    def with_text_kwargs(self, index: int, **kwargs) -> Modal:
        modal = self.__get_self()

        if not isinstance(modal.components[0].components[index], TextInput):
            raise ValueError(f'Component at index {index} is not a TextInput')

        components = list(modal.components[0].components)

        components[index] = components[index].model_copy(
            update=kwargs,
            deep=True
        )

        modal.components[0].components = components

        return modal

    def with_extra(
        self,
        *extra: CustomIdExtraTypeType
    ) -> Modal:
        modal = self.__get_self()
        modal.extra = modal.extra or []

        for value in extra:
            parsed = ''
            match value:
                case None:
                    parsed = str(CustomIdExtraType.NONE)
                case str():
                    parsed = f'{CustomIdExtraType.STRING}{value}'
                case bool():
                    parsed = f'{CustomIdExtraType.BOOLEAN}{int(value)}'
                case int():
                    parsed = f'{CustomIdExtraType.INTEGER}{value}'
                case User():
                    parsed = f'{CustomIdExtraType.USER}{value.id}'
                case Channel():
                    parsed = f'{CustomIdExtraType.CHANNEL}{value.id}'
                case ProxyMember():
                    parsed = f'{CustomIdExtraType.MEMBER}{value.id}'
                case Group():
                    parsed = f'{CustomIdExtraType.GROUP}{value.id}'
                case Message():
                    parsed = f'{CustomIdExtraType.MESSAGE}{
                        value.channel_id}:{value.id}'
                case _:
                    raise ValueError(f'invalid extra type `{type(value)}`')

            modal.extra.append(parsed)

        if len('.'.join([modal.custom_id] + (modal.extra))) > 100:
            raise ValueError(
                'custom_id (with extra) must be less than 100 characters'
            )

        return modal
