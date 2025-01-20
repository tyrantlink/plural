from .redis import BaseRedisModel
from pydantic import BaseModel
from aredis_om import Field


class Guild(BaseRedisModel):
    class Meta:
        model_key_prefix = 'guild'

    class Config(BaseModel):
        logclean: bool = Field(
            default=False,
            description='whether the log cleaning is enabled')

    id: str = Field(
        primary_key=True,
        description='the guild id')
    config: Config = Field(
        default_factory=Config,
        description='guild config')
