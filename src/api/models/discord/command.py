from .enums import CommandType, IntegrationType, InteractionContextType
from pydantic import BaseModel


class Command(BaseModel):
    id: str
    type: CommandType
    application_id: str
    guild_id: str | None
    name: str
    name_localizations: dict | None
    description: str
    description_localizations: dict | None
    options: list[dict] | None
    default_member_permissions: str
    dm_permission: bool | None
    default_permission: bool | None
    nsfw: bool | None
    integration_types: list[IntegrationType] | None
    contexts: list[InteractionContextType] | None
    version: str
    handler: int  # entry point command handler type
