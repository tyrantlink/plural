from __future__ import annotations
from .enums import InteractionType, ApplicationCommandType, ApplicationCommandOptionType, Permission, EntitlementType, ApplicationIntegrationType, InteractionContextType  # , ComponentType
from .component import Component  # , SelectOption
from .response import InteractionResponse
from src.discord.types import Snowflake
from pydantic import model_validator
from .resolved import Resolved
from .base import RawBaseModel
from datetime import datetime
from .message import Message
from .channel import Channel
from .member import Member
from .guild import Guild
from .user import User


class ApplicationCommandInteractionDataOption(RawBaseModel):
    name: str
    type: ApplicationCommandOptionType
    value: str | int | float | bool | None = None
    options: list[ApplicationCommandInteractionDataOption] | None = None
    focused: bool | None = None


class ApplicationCommandInteractionData(RawBaseModel):
    id: Snowflake
    name: str
    type: ApplicationCommandType
    resolved: Resolved | None = None
    options: list[ApplicationCommandInteractionDataOption] | None = None
    guild_id: Snowflake | None = None
    target_id: Snowflake | None = None


class MessageComponentInteractionData(RawBaseModel):
    custom_id: str
    # component_type: ComponentType
    # values: list[SelectOption] | None = None
    resolved: Resolved | None = None


class ModalSubmitInteractionData(RawBaseModel):
    custom_id: str
    components: list[Component] | None = None


class Entitlement(RawBaseModel):
    id: Snowflake
    sku_id: Snowflake
    application_id: Snowflake
    user_id: Snowflake | None = None
    type: EntitlementType
    deleted: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    guild_id: Snowflake | None = None
    consumed: bool | None = None


class Interaction(RawBaseModel):
    id: Snowflake
    application_id: Snowflake
    type: InteractionType
    data: ApplicationCommandInteractionData | MessageComponentInteractionData | ModalSubmitInteractionData | None = None
    guild: Guild | None = None
    guild_id: Snowflake | None = None
    channel: Channel | None = None
    channel_id: Snowflake | None = None
    member: Member | None = None
    user: User | None = None
    token: str
    version: int
    message: Message | None = None
    # ! remember to also check user permissions for userproxy
    app_permissions: Permission | None = None
    locale: str | None = None
    guild_locale: str | None = None
    entitlements: list[Entitlement] | None = None
    authorizing_integration_owners: dict[
        ApplicationIntegrationType, Snowflake] | None = None
    context: InteractionContextType | None = None
    response: InteractionResponse

    @model_validator(mode='before')
    @classmethod
    def ensure_response(cls, data: dict) -> dict:
        # ? set in .populate()
        data['response'] = None
        return data

    @property
    def author(self) -> Member | User:
        if self.user is None:
            assert self.member is not None
            return self.member

        return self.user

    @property
    def author_id(self) -> Snowflake:
        if isinstance(self.author, User):
            return self.author.id
        assert self.author.user is not None
        return self.author.user.id

    async def populate(self) -> None:
        # ? interactions return partials, make sure to get the full objects
        await super().populate()
        self.response = InteractionResponse(self)

        if self.channel_id is not None:
            self.channel = await Channel.fetch(self.channel_id)

        if self.guild_id is not None:
            self.guild = await Guild.fetch(self.guild_id)

        if self.member is not None and self.guild_id is not None:
            self.member = await Member.fetch(self.guild_id, self.author_id)

        if self.user is not None:
            self.user = await User.fetch(self.author_id)
