from __future__ import annotations

from redis.asyncio import BlockingConnectionPool, Redis
from aredis_om import Migrator

from .autoproxy import AutoProxy
from .group import Group
from .guild import Guild
from .interaction import Interaction
from .member import ProxyMember
from .message import Message
from .proxy_log import ProxyLog
from .share import Share
from .user import User


async def redis_init(redis_url: str) -> None:
    # ? it seems to just not run with more than 100 connections
    pool = BlockingConnectionPool.from_url(
        redis_url,
        decode_responses=True,
        max_connections=100
    )

    for model in (
        AutoProxy,
        Group,
        Guild,
        Interaction,
        ProxyMember,
        Message,
        ProxyLog,
        Share,
        User
    ):
        model._meta.database = Redis(connection_pool=pool)

    await Migrator().run()
