from pymongo import IndexModel
from datetime import datetime
from beanie import Document
from pydantic import Field


class DiscordCache(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'discord_cache'
        validate_on_save = True
        indexes = [  # ? one hour expiration
            IndexModel('ts', expireAfterSeconds=60*60),
            'snowflake',
            IndexModel([('snowflake', 1), ('guild_id', 1)], unique=True)
        ]

    snowflake: int = Field(  # type: ignore
        description='snowflake id of the discord object')
    guild_id: int | None = Field(
        default=None,
        description='snowflake id of the guild, if applicable')
    data: dict = Field(
        description='the data of the discord object')
    deleted: bool = Field(
        default=False,
        description='whether the object has been deleted')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp for ttl index')
