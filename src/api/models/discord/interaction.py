from .enums import InteractionType, InteractionContextType
from pydantic import BaseModel, Field


class Interaction(BaseModel):
    id: str
    application_id: str
    type: InteractionType
    data: dict | None
    guild: dict | None
    guild_id: str | None
    channel: dict | None
    channel_id: str | None
    member: dict | None
    user: dict | None
    token: str
    version: int
    message: dict | None
    app_permissions: str
    locale: str | None
    guild_locale: str | None
    entitlements: list[dict]
    authorizing_integration_owners: dict
    context: InteractionContextType | None
