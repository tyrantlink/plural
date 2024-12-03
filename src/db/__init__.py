from .userproxy_interaction import UserProxyInteraction
from pymongo import AsyncMongoClient
from .group_share import GroupShare
from .helpers import ImageExtension
from .cfcdnproxy import CFCDNProxy
from .httpcache import HTTPCache
from .events import GatewayEvent
from .api_token import ApiToken
from .member import ProxyMember
from src.models import project
from beanie import init_beanie
from .webhook import Webhook
from .message import Message
from .api_key import ApiKey
from .config import Config
from .group import Group
from .latch import Latch
from .reply import Reply
from logfire import span
from .log import Log


class MongoDatabase:
    def __init__(self, mongo_uri: str) -> None:
        self._client = AsyncMongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            readPreference='nearest',
        )['plural']

    async def _init_beanie(self) -> None:
        await init_beanie(
            self._client,  # type: ignore #? beanie still based on motor
            document_models=[
                UserProxyInteraction,
                GatewayEvent,
                ProxyMember,
                CFCDNProxy,
                GroupShare,
                HTTPCache,
                ApiToken,
                Webhook,
                Message,
                Config,
                ApiKey,
                Group,
                Latch,
                Reply,
                Log,
            ]
        )

    async def connect(self) -> None:
        if project.logfire_token:
            with span('MongoDB init'):
                await self._init_beanie()
            return

        await self._init_beanie()
