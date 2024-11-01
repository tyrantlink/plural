from __future__ import annotations
from .data import CommandInteractionData, ModalInteractionData, InteractionData
from ..enums import InteractionType, InteractionContextType
from .response import InteractionResponse
from ..guild import PartialGuild
from ..channel import Channel
from ..member import Member
from ..user import User


class Interaction(InteractionResponse):
    type: InteractionType
    data: InteractionData | None = None
    guild: PartialGuild | None = None
    guild_id: str | None = None
    channel: Channel | None = None
    channel_id: str | None = None
    member: Member | None = None
    user: User | None = None
    version: int
    message: dict | None = None  # !
    locale: str | None = None
    guild_locale: str | None = None
    entitlements: list[dict]
    authorizing_integration_owners: dict
    context: InteractionContextType | None = None

    @property
    def author(self) -> User | Member | None:
        return self.member or self.user
