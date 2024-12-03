from datetime import datetime, timedelta
from collections.abc import Mapping
from pymongo import IndexModel
from typing import Any, Self
from beanie import Document
from pydantic import Field


def _merge_dicts(*dicts: Mapping[Any, Any]) -> dict:
    """priority left to right (e.g. _merge_dicts({1: 1}, {1: 2}) -> {1: 2})"""
    out = {}
    for d in dicts:
        for k, v in d.items():
            if isinstance(v, Mapping):
                out[k] = _merge_dicts(out.get(k, {}), v)
            else:
                out[k] = v
    return out


class DiscordObject(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'discord_objects'
        validate_on_save = True
        indexes = [  # ? one hour expiration
            IndexModel('ts', expireAfterSeconds=60*60)
        ]

    id: int = Field(  # type: ignore
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

    def merge(self, data: dict) -> Self:
        self.data = _merge_dicts(self.data, data)
        return self
