from .redis import BaseRedisModel
from pydantic import BaseModel
from aredis_om import Field

from .enums import ReplyFormat, SupporterTier


class User(BaseRedisModel):
    class Meta:
        model_key_prefix = 'user'

    class Config(BaseModel):
        reply_format: ReplyFormat = Field(
            default=ReplyFormat.INLINE,
            description='format for message references in servers')
        dm_reply_format: ReplyFormat = Field(
            default=ReplyFormat.INLINE,
            description='format for message references in dms')
        userproxy_ping_replies: bool = Field(
            default=False,
            description='whether to ping when you reply to someone')
        groups_in_autocomplete: bool = Field(
            default=True,
            description='whether to show groups in member autocomplete')

    class Data(BaseModel):
        supporter_tier: SupporterTier = Field(
            default=SupporterTier.NONE,
            description='the supporter tier of the user')
        applications: list[str] = Field(  # ! should probably be a dictionary with id as key and scopes as value
            default_factory=list,
            description='the applications the user has authorized')
        image_limit: int = Field(
            default=1000,
            description='the maximum number of images a user can upload')
        images: int = Field(
            default=0,
            description='the number of images a user has uploaded')
        sp_token: str | None = Field(
            None,
            description='the simply plural token of the user')
        sp_id: str | None = Field(
            None,
            description='the simply plural system id of the user')

    id: str = Field(
        primary_key=True,
        description='the user id')
    config: Config = Field(
        default_factory=Config,
        description='user config')
    data: Data = Field(
        default_factory=Data,
        description='user data')
