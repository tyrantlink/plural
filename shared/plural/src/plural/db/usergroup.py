from typing import ClassVar, Self
from datetime import timedelta
from secrets import token_hex
from hashlib import sha256
from time import time

from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from bcrypt import hashpw, gensalt

from plural.crypto import encode_b66, TOKEN_EPOCH

from .enums import ReplyFormat, SupporterTier, ApplicationScope, PaginationStyle
from .member import ProxyMember
from .base import BaseDocument
from .group import Group


class Usergroup(BaseDocument):
    class Settings:
        name = 'usergroups'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            'users'
        ]

    class Config(BaseModel):
        account_tag: str = Field(
            default='',
            description='the global account tag; overridden by group tags')
        reply_format: ReplyFormat = Field(
            default=ReplyFormat.INLINE,
            description='format for message references in servers')
        groups_in_autocomplete: bool = Field(
            default=True,
            description='whether to show groups in member autocomplete')
        pagination_style: PaginationStyle = Field(
            default=PaginationStyle.BASIC_ARROWS,
            description='the style of pagination buttons to use')
        roll_embed: bool = Field(
            default=True,
            description='whether to show for dice rolls')
        tag_format: str = Field(
            default='{tag}',
            description='the format for tags in member names')
        pronoun_format: str = Field(
            default='({pronouns})',
            description='the format for pronouns in member names')
        include_tag: bool = Field(
            default=True,
            description='whether to include the account/group tag in the member name')
        include_pronouns: bool = Field(
            default=True,
            description='whether to include the pronouns in the member name')
        display_name_order: list[int] = Field(
            default_factory=lambda: [0, 1, 2],
            description='The order of display name components (0 = name, 1 = tag, 2 = pronouns)')
        private_member_info: bool = Field(
            default=False,
            description='whether to show member details in the proxy info command'
        )

    class UserproxyConfig(BaseModel):
        reply_format: ReplyFormat = Field(
            default=ReplyFormat.INLINE,
            description='format for message references in servers')
        dm_reply_format: ReplyFormat = Field(
            default=ReplyFormat.INLINE,
            description='format for message references in dms')
        ping_replies: bool = Field(
            default=False,
            description='whether to ping when you reply to someone')
        include_tag: bool = Field(
            default=False,
            description='whether to include the tag in the member name')
        include_pronouns: bool = Field(
            default=False,
            description='whether to include the pronouns in the member name')
        attachment_count: int = Field(
            default=1,
            description='the number of attachment options to include in the proxy command')
        self_hosted: bool = Field(
            default=False,
            description='whether the userproxy is self-hosted')
        required_message_parameter: bool = Field(
            default=False,
            description='whether the proxy command requires the message parameter')
        name_in_reply_command: bool = Field(
            default=True,
            description='whether the name should be included in the reply command')
        include_attribution: bool = Field(
            default=True,
            description='whether to include attribution at the end of bio')

    class Data(BaseModel):
        selfhosting_token: str | None = Field(
            None,
            description='the self-hosting token of the user')
        userproxy_version: str | None = Field(
            None,
            description='hash of last response to GET /userproxies')
        supporter_tier: SupporterTier = Field(
            default=SupporterTier.NONE,
            description='the supporter tier of the user')
        applications: dict[str, ApplicationScope] = Field(
            default_factory=dict,
            description='the applications the user has authorized')
        image_limit: int = Field(
            default=5000,
            description='the maximum number of images a user can upload')
        sp_token: str | None = Field(
            None,
            description='the simply plural token of the user')
        sp_id: str | None = Field(
            None,
            description='the simply plural system id of the user'
        )

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='internal usergroup id')
    users: set[int] = Field(
        description='the user ids in the usergroup')
    config: Config = Field(
        default_factory=Config,
        description='the user config')
    userproxy_config: UserproxyConfig = Field(
        default_factory=UserproxyConfig,
        description='default base userproxy config')
    data: Data = Field(
        default_factory=Data,
        description='the user data')

    @classmethod
    async def get_by_user(
        cls,
        user_id: int,
        use_cache: bool = True
    ) -> Self:
        return (
            await Usergroup.find_one({
                'users': user_id
            }, ignore_cache=not use_cache) or
            await Usergroup(
                users={user_id}
            ).save()
        )

    async def get_avatar_count(self, user_id: int) -> int:
        groups = await Group.find({
            '$or': [
                {'account': self.id},
                {f'users.{user_id}': {'$exists': True}}]
        }, projection_model=AvatarOnlyGroup).to_list()

        members = await ProxyMember.find({'_id': {'$in': list({
            member_id
            for group in groups
            for member_id in group.members
        })}}, projection_model=AvatarOnlyMember).to_list()

        avatars = {
            *[group.avatar for group in groups],
            *[member.avatar for member in members],
            *[
                tag.avatar
                for member in members
                for tag in member.proxy_tags
            ]
        }

        avatars.discard(None)

        return len(avatars)

    async def update_token(self) -> str:
        from . import redis

        token = '.'.join([
            encode_b66(int.from_bytes(self.id.binary)),
            encode_b66(int((time()*1000)-TOKEN_EPOCH)),
            encode_b66(int(token_hex(20), 16))
        ])

        if self.data.selfhosting_token:
            await redis.delete(
                'token:' + sha256(
                    '.'.join(self.data.selfhosting_token.split(
                        '.')[:2]).encode()
                ).hexdigest()
            )

        self.data.selfhosting_token = hashpw(
            token.encode(),
            gensalt()
        ).decode()

        await self.save()

        return token


class AvatarOnlyGroup(BaseModel):
    avatar: str | None
    members: list[PydanticObjectId]


class AvatarOnlyMember(BaseModel):
    avatar: str | None
    proxy_tags: list[ProxyMember.ProxyTag]
