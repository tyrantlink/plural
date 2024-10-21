from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie, PydanticObjectId
from typing import Type, overload, Literal
from src.models import ReplyAttachment
from bcrypt import hashpw, gensalt
from .models import DatalessImage
from .userproxy import UserProxy
from secrets import token_hex
from .webhook import Webhook
from .message import Message
from .api_key import ApiKey
from .member import Member
from .group import Group
from .latch import Latch
from .image import Image
from .reply import Reply
from time import time


class _MongoNew:
    @staticmethod
    def webhook(id: int, guild: int, url: str) -> Webhook:
        return Webhook(
            id=id,
            guild=guild,
            url=url
        )

    @staticmethod
    def message(
        original_id: int,
        proxy_id: int,
        author_id: int
    ) -> Message:
        return Message(
            original_id=original_id,
            proxy_id=proxy_id,
            author_id=author_id
        )

    @staticmethod
    def group(
        name: str
    ) -> Group:
        return Group(
            name=name,
            avatar=None,
            tag=None
        )

    @staticmethod
    def image(
        data: bytes,
        extension: str
    ) -> Image:
        return Image(data=data, extension=extension)

    @staticmethod
    def latch(
        user: int,
        guild: int,
        member: PydanticObjectId | None,
        enabled: bool = False
    ) -> Latch:
        return Latch(
            user=user,
            guild=guild,
            enabled=enabled,
            member=member
        )

    @staticmethod
    def api_key(
        user: int
    ) -> tuple[ApiKey, str]:
        # ? placed here to avoid circular import
        from src.helpers import encode_b66, TOKEN_EPOCH

        token = '.'.join([
            encode_b66(user),
            encode_b66(int((time()*1000)-TOKEN_EPOCH)),
            encode_b66(int(token_hex(20), 16))
        ])
        return (
            ApiKey(
                id=user,
                token=hashpw(token.encode(), gensalt()).decode()
            ),
            token
        )

    @staticmethod
    def userproxy(
        bot_id: int,
        user_id: int,
        member: PydanticObjectId,
        public_key: str,
        token: str | None = None
    ) -> UserProxy:
        return UserProxy(
            bot_id=bot_id,
            user_id=user_id,
            member=member,
            public_key=public_key,
            token=token
        )


class MongoDatabase:
    def __init__(self, mongo_uri: str) -> None:
        self._client: AsyncIOMotorDatabase = AsyncIOMotorClient(
            mongo_uri, serverSelectionTimeoutMS=5000)['plural']

    async def connect(self) -> None:
        await init_beanie(self._client, document_models=[
            Webhook, Message, Group, Member, Image, Latch, ApiKey, UserProxy, Reply
        ])

    @property
    def new(self) -> Type[_MongoNew]:
        return _MongoNew

    async def webhook(self, id: int) -> Webhook | None:
        return await Webhook.find_one({'_id': id})

    async def message(
        self,
        *,
        original_id: int | None = None,
        proxy_id: int | None = None
    ) -> Message | None:
        if original_id is not None and proxy_id is not None:
            raise ValueError('cannot provide both original_id and proxy_id')

        if original_id is None and proxy_id is None:
            raise ValueError('must provide either original_id or proxy_id')

        return await Message.find_one((
            {'original_id': original_id}
            if original_id else
            {'proxy_id': proxy_id}
        ))

    async def group(self, id: PydanticObjectId) -> Group | None:
        return await Group.find_one({'_id': id})

    async def member(self, id: PydanticObjectId) -> Member | None:
        return await Member.find_one({'_id': id})

    @overload
    async def image(self, id: PydanticObjectId, include_data: Literal[False]) -> DatalessImage | None:
        ...

    @overload
    async def image(self, id: PydanticObjectId, include_data: Literal[True] = True) -> Image | None:
        ...

    async def image(self, id: PydanticObjectId, include_data: bool = True) -> Image | DatalessImage | None:
        return await Image.find_one(
            {'_id': id},
            projection_model=None if include_data else DatalessImage
        )

    async def groups(self, user_id: int) -> list[Group]:
        return await Group.find({'accounts': user_id}).to_list()

    async def group_by_name(self, user_id: int, name: str) -> Group | None:
        return await Group.find_one({'accounts': user_id, 'name': name})

    @overload
    async def latch(self, user_id: int, guild_id: int, create: Literal[False] = False) -> Latch | None:
        ...

    @overload
    async def latch(self, user_id: int, guild_id: int, create: Literal[True]) -> Latch:
        ...

    async def latch(self, user_id: int, guild_id: int, create: bool = False) -> Latch | None:
        latch = await Latch.find_one({'user': user_id, 'guild': guild_id})
        if latch is not None or not create:
            return latch

        return self.new.latch(user_id, guild_id, None)

    async def api_key(self, user_id: int) -> ApiKey | None:
        return await ApiKey.find_one({'_id': user_id})

    async def userproxy(self, bot_id: int, member_id: PydanticObjectId) -> UserProxy | None:
        return await UserProxy.find_one({'bot_id': bot_id, 'member': member_id})

    async def userproxies(self, user_id: int) -> list[UserProxy]:
        return await UserProxy.find({'user_id': user_id}).to_list()
