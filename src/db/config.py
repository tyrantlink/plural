from pydantic import BaseModel, Field
from .enums import ReplyFormat
from beanie import Document
from typing import Self


class Config(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'config'
        is_root = True
        validate_on_save = True
        use_state_management = True

    id: int = Field(  # pyright: ignore #? unknown pyright rule
        description='either guild id or user id; currently always guild id')

    @classmethod
    def default(cls) -> Self:
        return cls(id=0)


class GuildConfig(Config):
    logclean: bool = Field(
        default=False,
        description='whether the log cleaning is enabled')


class UserConfig(Config):
    class Data(BaseModel):
        image_limit: int = Field(
            default=1000,
            description='the maximum number of images a user can upload')
        images: int = Field(
            default=0,
            description='the number of images a user has uploaded')

    reply_format: ReplyFormat = Field(
        default=ReplyFormat.INLINE,
        description='format for message references in servers')
    dm_reply_format: ReplyFormat = Field(
        default=ReplyFormat.INLINE,
        description='format for message references in dms')
    userproxy_ping_replies: bool = Field(
        default=False,
        description='whether to ping when you reply to someone')
    data: Data = Field(
        default_factory=Data,
        description='user specific data, stored in config because i don\'t want to make a new collection')

    @classmethod
    async def inc_images(cls, user_id: int) -> None:
        if (await cls.get_motor_collection().update_one(
            {'_id': user_id}, {'$inc': {'data.images': 1}}
        )).modified_count != 0:
            return

        await cls(
            id=user_id,
            data=cls.Data(images=1)
        ).insert()

    @classmethod
    async def dec_images(cls, user_id: int) -> None:
        await cls.get_motor_collection().update_one(
            {'_id': user_id},
            {'$inc': {'data.images': -1}}
        )
