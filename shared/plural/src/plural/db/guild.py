from datetime import timedelta

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
