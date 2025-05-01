from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field, field_validator

from plural.missing import MISSING, is_not_missing
from plural.db import ProxyMember, Group

from src.discord.models.base import RawBaseModel, PydanticArbitraryType

from src.discord.enums import (
    CustomIdExtraType,
    DefaultValueType,
    TextInputStyle,
    ComponentType,
    ButtonStyle,
    ChannelType
)


if TYPE_CHECKING:
    from src.discord.types import Snowflake
    from plural.missing import Optional

    from .command import InteractionCallback
    from .expression import Emoji

    from src.events.interaction import CustomIdExtraTypeType


__all__ = (
    'ActionRow',
    'Button',
    'Component',
    'MessageComponent',
    'SelectMenu',
    'TextInput',
)


class MessageComponent(RawBaseModel):
    type: ComponentType

    @field_validator('type', mode='before')
    @classmethod
    def validate_type(cls, value: ComponentType | int) -> ComponentType:
        return ComponentType(value)


class Button(MessageComponent):
    type: Literal[ComponentType.BUTTON] = ComponentType.BUTTON
    """`2` for a button"""
    style: ButtonStyle
    """A button style"""
    label: Optional[str]
    """Text that appears on the button; max 80 characters"""
    emoji: Optional[Emoji]
    """`name`, `id`, and `animated`"""
    custom_id: Optional[str]
    """Developer-defined identifier for the button; max 100 characters"""
    sku_id: Optional[Snowflake]
    """Identifier for a purchasable SKU, only available when using premium-style buttons"""
    url: Optional[str]
    """URL for link-style buttons"""
    disabled: Optional[bool]
    """Whether the button is disabled (defaults to `false`)"""
    # ? library stuff
    callback: Optional[Annotated[
        InteractionCallback,
        PydanticArbitraryType
    ]] = Field(None, exclude=True)

    def as_payload(self) -> dict:
        json = super().as_payload()

        # ? because the snowflake type serializes to a string
        # ? it doesn't not serialize the missing value
        # ? for some reason, i'm too tired to figure out why
        if not is_not_missing(self.sku_id):
            json.pop('sku_id')

        return json

    def with_overrides(
        self,
        style: Optional[ButtonStyle] = MISSING,
        label: Optional[str] = MISSING,
        emoji: Optional[Emoji] = MISSING,
        sku_id: Optional[Snowflake] = MISSING,
        url: Optional[str] = MISSING,
        disabled: Optional[bool] = MISSING,
        extra: Optional[list[CustomIdExtraTypeType]] = MISSING
    ) -> Button:
        return self.model_copy(
            update={
                k: v
                for k, v in {
                    'style': style,
                    'label': label,
                    'emoji': emoji,
                    'sku_id': sku_id,
                    'url': url,
                    'disabled': disabled,
                    'custom_id': (
                        self.custom_id
                        if not extra
                        else parse_extra(self.custom_id, extra))
                }.items()
                if is_not_missing(v)},
            deep=True
        )


class SelectMenu(MessageComponent):
    class Option(RawBaseModel):
        label: str
        """User-facing name of the option; max 100 characters"""
        value: str
        """Dev-defined value of the option; max 100 characters"""
        description: Optional[str]
        """Additional description of the option; max 100 characters"""
        emoji: Optional[Emoji]
        """`id`, `name`, and `animated`"""
        default: Optional[bool]
        """Will show this option as selected by default"""

    class DefaultValue(RawBaseModel):
        id: Snowflake
        """ID of a user, role, or channel"""
        type: DefaultValueType
        """Type of value that id represents. Either "user", "role", or "channel" """

    type: Literal[
        ComponentType.STRING_SELECT,
        ComponentType.USER_SELECT,
        ComponentType.ROLE_SELECT,
        ComponentType.MENTIONABLE_SELECT,
        ComponentType.CHANNEL_SELECT]
    """Type of select menu component (text: `3`, user: `5`, role: `6`, mentionable: `7`, channels: `8`)"""
    custom_id: str
    """ID for the select menu; max 100 characters"""
    options: Optional[list[Option]]
    """Specified choices in a select menu (only required and available for string selects (type `3`); max 25"""
    channel_types: Optional[list[ChannelType]]
    """List of channel types to include in the channel select component (type `8`)"""
    placeholder: Optional[str]
    """Placeholder text if nothing is selected; max 150 characters"""
    default_values: Optional[list[DefaultValue]]
    """	List of default values for auto-populated select menu components; number of default values must be in the range defined by `min_values` and `max_values`"""
    min_values: Optional[int]
    """Minimum number of items that must be chosen (defaults to 1); min 0, max 25"""
    max_values: Optional[int]
    """Maximum number of items that can be chosen (defaults to 1); max 25"""
    disabled: Optional[bool]
    """Whether select menu is disabled (defaults to `false`)"""
    # ? library stuff
    callback: Optional[Annotated[
        InteractionCallback,
        PydanticArbitraryType
    ]] = Field(None, exclude=True)

    def with_overrides(
        self,
        options: Optional[list[Option]] = MISSING,
        placeholder: Optional[str] = MISSING,
        default_values: Optional[list[DefaultValue]] = MISSING,
        min_values: Optional[int] = MISSING,
        max_values: Optional[int] = MISSING,
        disabled: Optional[bool] = MISSING,
        extra: Optional[list[CustomIdExtraTypeType]] = MISSING
    ) -> SelectMenu:
        return self.model_copy(
            update={
                k: v
                for k, v in {
                    'custom_id': (
                        self.custom_id
                        if not extra
                        else parse_extra(self.custom_id, extra)),
                    'options': options,
                    'placeholder': placeholder,
                    'default_values': default_values,
                    'min_values': min_values,
                    'max_values': max_values,
                    'disabled': disabled
                }.items()
                if is_not_missing(v)},
            deep=True
        )


class TextInput(MessageComponent):
    type: Literal[ComponentType.TEXT_INPUT] = ComponentType.TEXT_INPUT
    """`4` for a text input"""
    custom_id: str
    """Developer-defined identifier for the input; max 100 characters"""
    style: Optional[TextInputStyle]
    """The Text Input Style"""
    label: Optional[str]
    """Label for this component; max 45 characters"""
    min_length: Optional[int]
    """Minimum input length for a text input; min 0, max 4000"""
    max_length: Optional[int]
    """Maximum input length for a text input; min 1, max 4000"""
    required: Optional[bool]
    """Whether this component is required to be filled (defaults to true)"""
    value: Optional[str]
    """Pre-filled value for this component; max 4000 characters"""
    placeholder: Optional[str]
    """Custom placeholder text if the input is empty; max 100 characters"""

    def with_overrides(
        self,
        style: Optional[TextInputStyle] = MISSING,
        label: Optional[str] = MISSING,
        min_length: Optional[int] = MISSING,
        max_length: Optional[int] = MISSING,
        required: Optional[bool] = MISSING,
        value: Optional[str] = MISSING,
        placeholder: Optional[str] = MISSING,
        extra: Optional[list[CustomIdExtraTypeType]] = MISSING
    ) -> TextInput:
        return self.model_copy(
            update={
                k: v
                for k, v in {
                    'custom_id': (
                        self.custom_id
                        if not extra
                        else parse_extra(self.custom_id, extra)),
                    'style': style,
                    'label': label,
                    'min_length': min_length,
                    'max_length': max_length,
                    'required': required,
                    'value': value,
                    'placeholder': placeholder
                }.items()
                if is_not_missing(v)},
            deep=True
        )


class Modal(RawBaseModel):
    title: str
    """Title of the popup modal, max 45 characters"""
    custom_id: str
    """Developer-defined identifier for the modal, max 100 characters"""
    components: list[ActionRow]
    """Between 1 and 5 (inclusive) components that make up the modal"""
    # ? library stuff
    callback: Optional[Annotated[
        InteractionCallback,
        PydanticArbitraryType
    ]] = Field(None, exclude=True)

    def with_overrides(
        self,
        title: Optional[str] = MISSING,
        text_inputs: Optional[list[TextInput]] = MISSING,
        extra: Optional[list[CustomIdExtraTypeType]] = MISSING
    ) -> SelectMenu:
        return self.model_copy(
            update={
                k: v
                for k, v in {
                    'custom_id': (
                        self.custom_id
                        if not extra
                        else parse_extra(self.custom_id, extra)),
                    'title': title or self.title,
                    'components': ([
                        ActionRow(components=[text_input])
                        for text_input in text_inputs]
                        if text_inputs
                        else self.components)
                }.items()
                if is_not_missing(v)},
            deep=True
        )


class ActionRow(MessageComponent):
    type: Literal[ComponentType.ACTION_ROW] = ComponentType.ACTION_ROW
    components: list[Button | SelectMenu | TextInput]


type Component = Button | SelectMenu | ActionRow


def parse_extra(
    custom_id: str,
    extra: list[CustomIdExtraTypeType]
) -> str:
    from .channel import Channel
    from .message import Message
    from .user import User

    for value in extra:
        match value:
            case None:
                custom_id += f'.{CustomIdExtraType.NONE}'
            case str():
                custom_id += f'.{CustomIdExtraType.STRING}{value}'
            case bool():
                custom_id += f'.{CustomIdExtraType.BOOLEAN}{int(value)}'
            case int():
                custom_id += f'.{CustomIdExtraType.INTEGER}{value}'
            case User():
                custom_id += f'.{CustomIdExtraType.USER}{value.id}'
            case Channel():
                custom_id += f'.{CustomIdExtraType.CHANNEL}{value.id}'
            case ProxyMember():
                custom_id += f'.{CustomIdExtraType.MEMBER}{value.id}'
            case Group():
                custom_id += f'.{CustomIdExtraType.GROUP}{value.id}'
            case Message():
                custom_id += f'.{CustomIdExtraType.MESSAGE}{value.channel_id}:{value.id}'
            case _:
                raise ValueError(f'invalid extra type `{type(value)}`')

    if len(custom_id) > 100:
        raise ValueError(
            'custom_id (with extra) must be less than 100 characters'
        )

    return custom_id
