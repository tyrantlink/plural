from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from .userproxy_interaction import UserProxyInteraction
from .httpcache import HTTPCache
from src.models import project
from beanie import init_beanie
from .webhook import Webhook
from .message import Message
from .api_key import ApiKey
from .member import Member
from .group import Group
from .latch import Latch
from .image import Image
from .reply import Reply
from logfire import span


class MongoDatabase:
    def __init__(self, mongo_uri: str) -> None:
        self._client: AsyncIOMotorDatabase = AsyncIOMotorClient(
            mongo_uri, serverSelectionTimeoutMS=5000)['plural2']

    async def _init_beanie(self) -> None:
        await init_beanie(
            self._client,
            document_models=[
                UserProxyInteraction,
                HTTPCache,
                Webhook,
                Message,
                ApiKey,
                Member,
                Group,
                Image,
                Latch,
                Reply,
            ]
        )

    async def connect(self) -> None:
        if project.logfire_token:
            with span('MongoDB init'):
                await self._init_beanie()
            return

        await self._init_beanie()
