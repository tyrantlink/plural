from __future__ import annotations
from src.models import project, MissingOr, MissingNoneOr, MISSING, _MissingType
from typing import ClassVar, TYPE_CHECKING, Self
from datetime import datetime, UTC
from pymongo import IndexModel
from .enums import CacheType
from beanie import Document
from pydantic import Field
import logfire

if TYPE_CHECKING:
    from collections.abc import Sequence


class DiscordCache(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'dev_cache' if project.dev_environment else 'discord_cache'
        validate_on_save = True
        indexes: ClassVar = [  # ? one day expiration
            IndexModel('ts', expireAfterSeconds=60*60*24),
            'snowflake',
            IndexModel([('snowflake', 1), ('guild_id', 1),
                       ('bot_id', 1)], unique=True)
        ]

    snowflake: int = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        description='snowflake id of the discord object')
    type: CacheType = Field(
        description='type of the discord object')
    guild_id: int | None = Field(
        default=None,
        description='snowflake id of the guild, if applicable')
    data: dict = Field(
        description='the data of the discord object')
    meta: dict = Field(
        default_factory=dict,
        description='additional metadata')
    deleted: bool = Field(
        default=False,
        description='whether the object has been deleted')
    error: int | None = Field(
        default=None,
        description='the http status code, if response was an error')
    bot_id: str | None = Field(
        default=None,
        description='id of bot used to fetch the object')
    ts: datetime | None = Field(
        default_factory=datetime.utcnow,
        description='timestamp for ttl index')

    @property
    def exception(self) -> Exception | None:
        from src.errors import NotFound, Forbidden, Unauthorized, HTTPException
        if self.error is None:
            return None

        base = f'{self.type.name.lower()} {self.snowflake}'

        match self.error:
            case 404:
                raise NotFound(f'{base} not found')
            case 403:
                raise Forbidden(f'{base} is forbidden')
            case 401:
                raise Unauthorized(f'{base} is unauthorized')
            case _:
                raise HTTPException(self.error)

    @classmethod
    async def get(  # pyright: ignore[reportIncompatibleMethodOverride]
        cls,
        snowflake: int,
        guild_id: MissingNoneOr[int] = MISSING,
        type: MissingOr[CacheType] = MISSING
    ) -> DiscordCache | None:
        query: dict[str, int | None] = {'snowflake': snowflake}

        if guild_id is not MISSING:
            assert not isinstance(guild_id, _MissingType)
            query['guild_id'] = guild_id

        if type is not MISSING:
            assert not isinstance(type, _MissingType)
            query['type'] = type.value

        return await cls.find_one(query)

    @classmethod
    async def get_many(
        cls,
        type: CacheType,
        guild_id: int | None = None,
        filter: dict | None = None
    ) -> Sequence[DiscordCache]:
        return await cls.find(
            {'type': type.value, 'guild_id': guild_id, **(filter or {})}
        ).to_list()

    @classmethod
    async def add(
        cls,
        type: CacheType,
        data: dict,
        guild_id: int | None = None
    ) -> None:
        from src.logic.cache import discord_cache, member_update, user_update
        from src.discord import GatewayEvent, GatewayEventName, GatewayOpCode

        match type:
            case CacheType.GUILD:
                name = GatewayEventName.GUILD_CREATE
            case CacheType.ROLE:
                name = GatewayEventName.GUILD_ROLE_CREATE
                data = {'role': data, 'guild_id': guild_id}
            case CacheType.CHANNEL:
                name = GatewayEventName.CHANNEL_CREATE
            case CacheType.EMOJI:
                name = GatewayEventName.GUILD_EMOJIS_UPDATE
            case CacheType.WEBHOOK:
                name = GatewayEventName.WEBHOOKS_UPDATE
            case CacheType.MESSAGE:
                name = GatewayEventName.MESSAGE_CREATE
            case CacheType.USER:
                return await user_update(data)
            case CacheType.MEMBER:
                if guild_id is None:
                    raise ValueError('guild_id is required for members')

                return await member_update(data, guild_id)
            case _:
                raise ValueError('invalid cache type')

        await discord_cache(GatewayEvent(
            op=GatewayOpCode.DISPATCH,
            t=name,
            d=data,
            s=0
        ))

        return None

    @classmethod
    async def http4xx(
        cls,
        status_code: int,
        type: CacheType,
        snowflake: int,
        guild_id: int | None = None
    ) -> None:
        if status_code < 400 or status_code >= 500:
            raise ValueError('status code must be 4xx')

        await cls.get_motor_collection().update_one(
            {'snowflake': snowflake, 'guild_id': guild_id},
            {
                '$set': {
                    'snowflake': snowflake,
                    'guild_id': guild_id,
                    'error': status_code,
                    'deleted': False,
                    'type': type.value,
                    'data': {},
                    'meta': {},
                    'ts': datetime.now(UTC),
                }
            },
            upsert=True
        )

    @classmethod
    async def get_channel(
        cls,
        channel_id: int,
        guild_id: int | None = None
    ) -> DiscordCache | None:
        return await cls.find_one({
            'snowflake': channel_id,
            'guild_id': guild_id,
            'type': CacheType.CHANNEL.value
        })

    @classmethod
    async def get_guild(
        cls,
        guild_id: int
    ) -> DiscordCache | None:
        return await cls.find_one({
            'snowflake': guild_id,
            'type': CacheType.GUILD.value
        })

    @classmethod
    async def get_member(
        cls,
        user_id: int,
        guild_id: int
    ) -> DiscordCache | None:
        member = await cls.get(user_id, guild_id)

        if member is None:
            return None

        user = await cls.get(user_id, None)

        if user is not None:
            member.data['user'] = user.data

        return member
