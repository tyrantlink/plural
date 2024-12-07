from .enums import ReplyFormat
from beanie import Document
from pydantic import Field
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

    id: int = Field(  # type: ignore
        description='either guild id or user id; currently always guild id')

    @classmethod
    def default(cls) -> Self:
        return cls(id=0)


class GuildConfig(Config):
    logclean: bool = Field(
        default=False,
        description='whether the log cleaning is enabled')


class UserConfig(Config):
    reply_format: ReplyFormat = Field(
        default=ReplyFormat.INLINE,
        description='format for message references')
    userproxy_reply_format: ReplyFormat = Field(
        default=ReplyFormat.INLINE,
        description='format for userproxy message references')
    userproxy_ping_replies: bool = Field(
        default=True,
        description='whether to ping when you reply to someone')
