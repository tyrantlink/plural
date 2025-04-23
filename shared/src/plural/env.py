from typing import Self
from os import environ

from pydantic import BaseModel
from bson import ObjectId

from .missing import MISSING


INSTANCE = str(ObjectId())


class Env(BaseModel):
    bot_token: str
    discord_url: str
    redis_url: str
    mongo_url: str
    domain: str
    max_avatar_size: int
    dev: bool
    cdn_upload_token: str
    admins: set[int]
    patreon_secret: str
    info_bot_token: str

    @classmethod
    def new(cls) -> Self:
        return cls.model_validate({
            'bot_token': environ.get('BOT_TOKEN', MISSING),
            'discord_url': environ.get('DISCORD_URL', MISSING),
            'redis_url': environ.get('REDIS_URL', MISSING),
            'mongo_url': environ.get('MONGO_URL', MISSING),
            'domain': environ.get('DOMAIN', MISSING),
            'max_avatar_size': int(environ.get('MAX_AVATAR_SIZE', MISSING)),
            'dev': environ.get('DEV', '1') != '0',
            'cdn_upload_token': environ.get('CDN_UPLOAD_TOKEN', MISSING),
            'admins': (
                set(map(int, environ.get('ADMINS', '').split(',')))
                if environ.get('ADMINS') else set()),
            'patreon_secret': environ.get('PATREON_SECRET', ''),
            'info_bot_token': environ.get('INFO_BOT_TOKEN', '')
        })

    @property
    def avatar_url(self) -> str:
        return (
            f'https://cdn{'dev' if self.dev else ''}'
            f'.{self.domain}/images/{{parent_id}}/{{hash}}.webp'
        )


env = Env.new()
