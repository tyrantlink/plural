from datetime import timedelta
from typing import Self

from pydantic import Field, BaseModel

from .base import BaseDocument


class Guild(BaseDocument):
    class Settings:
        name = 'guilds'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)

    class Config(BaseModel):
        logclean: bool = Field(
            default=False,
            description='whether the log cleaning is enabled')
        force_include_tag: bool = Field(
            default=False,
            description='whether to force include tag in member names')
        log_channel: int | None = Field(
            None,
            description='the channel id for logging proxy messages'
        )

    id: int = Field(
        description='the id of the guild')
    config: Config = Field(
        default_factory=Config,
        description='guild config'
    )

    @classmethod
    async def get_by_id(
        cls,
        guild_id: int,
        use_cache: bool = True
    ) -> Self:
        return (
            await Guild.get(guild_id, ignore_cache=not use_cache) or
            await Guild(
                id=guild_id
            ).save()
        )
