from redis.asyncio import Redis, BlockingConnectionPool
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from plural.otel import span
from plural.env import env

from .application import Application
from .autoproxy import Autoproxy
from .migration import Migration
from .usergroup import Usergroup
from .proxy_log import ProxyLog
from .member import ProxyMember
from .message import Message
from .group import Group
from .guild import Guild
from .reply import Reply
from .share import Share


__all__ = (
    'Application',
    'Autoproxy',
    'Group',
    'Guild',
    'Message',
    'Migration',
    'ProxyLog',
    'ProxyMember',
    'Reply',
    'Share',
    'Usergroup',
    'mongo_init',
    'redis',
    'redis_init',
)

redis: Redis


async def mongo_init() -> None:
    with span('initializing mongo'):
        await init_beanie(
            AsyncIOMotorClient(env.mongo_url)['plural'],
            document_models=[
                Application,
                Autoproxy,
                Group,
                Guild,
                Message,
                Migration,
                ProxyLog,
                ProxyMember,
                Reply,
                Share,
                Usergroup,
            ]
        )


async def redis_init() -> None:
    global redis

    with span('initializing redis'):
        pool: BlockingConnectionPool = BlockingConnectionPool.from_url(
            env.redis_url,
            decode_responses=True,
            max_connections=100
        )

        redis = Redis(connection_pool=pool)
