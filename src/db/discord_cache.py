from __future__ import annotations
from src.models import MissingNoneOr, MISSING
from datetime import datetime, UTC
from pymongo import IndexModel
from .enums import CacheType
from typing import Sequence
from beanie import Document
from pydantic import Field
import logfire


class DiscordCache(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'discord_cache'
        validate_on_save = True
        indexes = [  # ? one day expiration
            IndexModel('ts', expireAfterSeconds=60*60*24),
            'snowflake',
            IndexModel([('snowflake', 1), ('guild_id', 1)], unique=True)
        ]

    snowflake: int = Field(  # type: ignore
        description='snowflake id of the discord object')
    type: CacheType = Field(
        description='type of the discord object')
    guild_id: int | None = Field(
        default=None,
        description='snowflake id of the guild, if applicable')
    data: dict = Field(
        description='the data of the discord object')
    deleted: bool = Field(
        default=False,
        description='whether the object has been deleted')
    error: int | None = Field(
        default=None,
        description='the http status code, if response was an error')
    ts: datetime | None = Field(
        default_factory=datetime.utcnow,
        description='timestamp for ttl index')

    @classmethod
    async def get(
        cls,
        snowflake: int,
        guild_id: MissingNoneOr[int] = MISSING
    ) -> DiscordCache | None:
        async def _get(cls, snowflake: int, guild_id: MissingNoneOr[int] = MISSING
                       ) -> DiscordCache | None:
            if guild_id is MISSING:
                return await cls.find_one({'snowflake': snowflake})

            return await cls.find_one({'snowflake': snowflake, 'guild_id': guild_id})

        cached = await _get(cls, snowflake, guild_id)

        if cached is None:
            logfire.debug(
                'cache miss: {snowflake}, {guild_id}',
                snowflake=snowflake,
                guild_id=guild_id
            )

        return cached

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

        await discord_cache(GatewayEvent(
            op=GatewayOpCode.DISPATCH,
            t=name,
            d=data,
            s=0
        ))

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
                    'ts': datetime.now(UTC).isoformat(),
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
        channel = await cls.find_one(
            {
                'snowflake': channel_id,
                'guild_id': (
                    guild_id
                    if guild_id is not None else
                    {'$ne': None}
                )
            }
        )

        return channel

    @classmethod
    async def get_guild(
        cls,
        guild_id: int
    ) -> DiscordCache | None:
        guild = await cls.get(guild_id, None)

        if guild is None or guild.error:
            return None

        guild.data['roles'] = [
            role.data
            for role in
            await cls.get_many(CacheType.ROLE, guild_id)
        ]

        return guild

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
