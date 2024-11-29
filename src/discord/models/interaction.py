from __future__ import annotations
from .enums import InteractionType, ApplicationCommandType, ApplicationCommandOptionType, Permission, EntitlementType, ApplicationIntegrationType, InteractionContextType, ComponentType
from .response import InteractionResponse, InteractionFollowup
from src.errors import Forbidden, NotFound
from src.discord.types import Snowflake
from pydantic import model_validator
from .component import ActionRow
from .resolved import Resolved
from src.models import project
from src.db import ProxyMember
from .base import RawBaseModel
from datetime import datetime
from .message import Message
from .channel import Channel
from typing import Protocol
from .member import Member
from .guild import Guild
from .user import User


class InteractionCallback(Protocol):
    async def __call__(self, interaction: Interaction, *args, **kwargs) -> None:
        ...


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
    component_type: ComponentType
    values: dict | None = None  # list[SelectOption] | None = None
    resolved: Resolved | None = None


class ModalSubmitInteractionData(RawBaseModel):
    custom_id: str
    # ? i think this is always a list of ActionRow
    components: list[ActionRow] | None = None


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
    followup: InteractionFollowup
    # ? library stuff
    proxy_member: ProxyMember | None = None

    @model_validator(mode='before')
    @classmethod
    def ensure_response(cls, data: dict) -> dict:
        # ? set in .populate()
        data['response'] = None
        data['followup'] = None
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

    @property
    def author_name(self) -> str:
        if isinstance(self.author, User):
            return self.author.username
        assert self.author.user is not None
        return self.author.user.username

    @property
    def send(self):
        return (
            self.followup.send
            if self.response.responded else
            self.response.send_message
        )

    async def populate(self) -> None:
        # ? interactions return partials, make sure to get the full objects
        await super().populate()
        self.response = InteractionResponse(self)
        self.followup = InteractionFollowup(self)

        if self.channel_id is not None:
            try:
                self.channel = await Channel.fetch(self.channel_id)
            except (Forbidden, NotFound):
                pass

        if self.guild_id is not None:
            try:
                self.guild = await Guild.fetch(self.guild_id)
            except (Forbidden, NotFound):
                pass

        if self.member is not None and self.guild is not None:
            try:
                self.member = await Member.fetch(self.guild.id, self.author_id)
            except (Forbidden, NotFound):
                pass

        if self.user is not None:
            try:
                self.user = await User.fetch(self.author_id)
            except (Forbidden, NotFound):
                pass

        if self.application_id != project.application_id:
            self.proxy_member = await ProxyMember.find_one(
                {'userproxy.bot_id': self.application_id})
