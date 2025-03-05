from __future__ import annotations

from typing import Self, TYPE_CHECKING

from pydantic import model_validator

from plural.missing import MISSING, Optional, Nullable

from src.discord.models.base import RawBaseModel
from src.discord.models.member import Member
from src.discord.models.guild import Guild
from src.discord.models.user import User

from src.discord.enums import MessageFlag

from .response import InteractionResponse, InteractionFollowup
from .data import (
    ApplicationCommandInteractionData,
    MessageComponentInteractionData,
    ModalSubmitInteractionData,
    InteractionData
)

if TYPE_CHECKING:
    from src.discord.types import Snowflake
    from src.core.http import File

    from src.discord.enums import (
        ApplicationIntegrationType,
        InteractionContextType,
        InteractionType,
        Permission,
    )

    from src.discord.models.component import MessageComponent
    from src.discord.models.entitlement import Entitlement
    from src.discord.models.message import AllowedMentions
    from src.discord.models.message import Message
    from src.discord.models.channel import Channel
    from src.discord.models.embed import Embed
    from src.discord.models.poll import Poll


__all__ = (
    'ApplicationCommandInteractionData',
    'Interaction',
    'MessageComponentInteractionData',
    'ModalSubmitInteractionData',
)


class Interaction(RawBaseModel):
    id: Snowflake
    """ID of the interaction"""
    application_id: Snowflake
    """ID of the application this interaction is for"""
    type: InteractionType
    """Type of interaction"""
    data: Optional[InteractionData]
    """Interaction data payload"""
    guild: Optional[Guild]
    """Guild that the interaction was sent from"""
    guild_id: Optional[Snowflake]
    """Guild that the interaction was sent from"""
    channel: Optional[Channel]
    """Channel that the interaction was sent from"""
    channel_id: Optional[Snowflake]
    """Channel that the interaction was sent from"""
    member: Optional[Member]
    """Guild member data for the invoking user, including permissions"""
    user: Optional[User]
    """User object for the invoking user, if invoked in a DM"""
    token: str
    """Continuation token for responding to the interaction"""
    version: int
    """Read-only property, always `1`"""
    message: Optional[Message]
    """For components, the message they were attached to"""
    app_permissions: Permission
    """Bitwise set of permissions the app has in the source location of the interaction"""
    locale: Optional[str]
    """Selected language of the invoking user"""
    guild_locale: Optional[str]
    """Guild's preferred locale, if invoked in a guild"""
    entitlements: list[Entitlement]
    """For monetized apps, any entitlements for the invoking user, representing access to premium SKUs"""
    authorizing_integration_owners: dict[ApplicationIntegrationType, Snowflake]
    """Mapping of installation contexts that the interaction was authorized for to related user or guild IDs. See Authorizing Integration Owners Object for details"""
    context: Optional[InteractionContextType]
    """Context where the interaction was triggered from"""
    # ? library stuff
    response: InteractionResponse
    followup: InteractionFollowup

    @model_validator(mode='before')
    @classmethod
    def pre_ensure_response(cls, data: dict) -> dict:
        # ? insert here so the validator doesn't get angry
        data['response'] = None
        data['followup'] = None
        return data

    @model_validator(mode='after')
    def post_ensure_response(self) -> Self:
        self.response = InteractionResponse(self)
        self.followup = InteractionFollowup(self)
        return self

    async def populate(self) -> None:
        await super().populate()

        if self.guild_id is not None:
            self.guild = await Guild.fetch(self.guild_id) or self.guild

    def send(
        self,
        content: Optional[Nullable[str]] = None,
        *,
        tts: Optional[bool] = MISSING,
        embeds: Optional[Nullable[list[Embed]]] = MISSING,
        allowed_mentions: Optional[Nullable[AllowedMentions]] = MISSING,
        flags: Optional[Nullable[MessageFlag]] = MessageFlag.EPHEMERAL,
        components: Optional[Nullable[list[MessageComponent]]] = MISSING,
        attachments: Optional[Nullable[list[File]]] = MISSING,
        poll: Optional[Nullable[Poll]] = MISSING,
        with_response: bool = False
    ) -> Message | None:
        args = {
            'content': content,
            'tts': tts,
            'embeds': embeds,
            'allowed_mentions': allowed_mentions,
            'flags': flags,
            'components': components,
            'attachments': attachments,
            'poll': poll,
            'with_response': with_response,
        }

        return (
            self.followup.send(**args)
            if self.response.responded else
            self.response.send_message(**args)
        )

    @property
    def author(self) -> Member | User:
        if self.user is MISSING:
            assert isinstance(self.member, Member)
            return self.member

        assert isinstance(self.user, User)
        return self.user

    @property
    def author_id(self) -> Snowflake:
        if isinstance(self.author, User):
            return self.author.id

        assert isinstance(self.author, Member)
        return self.author.user.id

    @property
    def author_name(self) -> str:
        if isinstance(self.author, User):
            return self.author.username
        assert self.author.user is not None
        return self.author.user.username

    async def process(self, latency: int) -> None:
        from src.events import on_interaction
        await self.populate()
        await on_interaction(self, latency)
