from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING, Any
from datetime import timedelta
from re import sub, IGNORECASE

from pydantic import Field, BaseModel, model_validator
from beanie import PydanticObjectId
from regex import compile

from plural.env import env

from .base import BaseDocument
from .guild import Guild

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from .usergroup import Usergroup
    from .group import Group


DOUBLESPACE = compile(r'\s{2,}')


class ProxyMember(BaseDocument):
    class Settings:
        name = 'members'
        validate_on_save = True
        use_cache = True
        cache_expiration_time = timedelta(milliseconds=500)
        indexes: ClassVar = [
            ('name', 'custom_id'),
            'userproxy.bot_id',
            'avatar'
        ]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @model_validator(mode='before')
    @classmethod
    def _handle_clyde(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        if (name := values.get('name')) is None:
            return values

        # ? just stolen from pluralkit https://github.com/PluralKit/PluralKit/blob/214a6d5a4933b975068b0272c98d178a47b487d5/src/pluralkit/bot/proxy.py#L62
        values['name'] = sub(
            '(c)(lyde)',
            '\\1\u200A\\2',
            name,
            flags=IGNORECASE
        )
        return values

    class ProxyTag(BaseModel):
        def __eq__(self, value: object) -> bool:
            return (
                isinstance(value, type(self)) and
                self.prefix == value.prefix and
                self.suffix == value.suffix and
                self.regex == value.regex and
                self.case_sensitive == value.case_sensitive
            )

        id: PydanticObjectId = Field(
            default_factory=PydanticObjectId,
            description='the id of the proxy tag')
        prefix: str = Field(
            '',
            max_length=50,
            description='tag must have a prefix or suffix')
        suffix: str = Field(
            '',
            max_length=50,
            description='tag must have a prefix or suffix')
        regex: bool = Field(
            False)
        case_sensitive: bool = Field(
            False)
        avatar: str | None = Field(
            None,
            description='the avatar hash of this proxy tag'
        )

        @model_validator(mode='after')
        def check_prefix_and_suffix(self) -> ProxyMember.ProxyTag:
            if not self.prefix and not self.suffix:
                raise ValueError('tag must have a prefix and/or suffix')
            return self

        @property
        def avatar_url(self) -> str | None:
            return env.avatar_url.format(
                parent_id=self.id,
                hash=self.avatar
            ) if self.avatar else None

        @property
        def name(self) -> str:
            return '​'.join([
                f'`{self.prefix}`' if self.prefix else '',
                '`text`',
                f'`{self.suffix}`' if self.suffix else ''
            ])

    class UserProxy(BaseModel):
        bot_id: int = Field(
            description='bot id')
        public_key: str = Field(
            description='the userproxy public key')
        token: str = Field(
            description='the userproxy bot token')
        command: str = Field(
            'proxy',
            description='name of the proxy command')
        guilds: set[int] = Field(
            default_factory=set,
            description='guilds the userproxy is enabled in'
        )

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the id of the member')
    name: str = Field(
        description='the name of the member',
        min_length=1,
        max_length=80)
    custom_id: str = Field(
        '',
        description='the custom identifier of the member; only shown in autocomplete',
        max_length=50)
    pronouns: str = Field(
        '',
        description='the pronouns of the member')
    bio: str = Field(
        '',
        description='the bio of the member',
        max_length=4000)
    birthday: str = Field(
        '',
        description='the birthday of the member')
    color: int | None = Field(
        None,
        description='the color of the member')
    avatar: str | None = Field(
        None,
        description='the avatar hash of the member')
    proxy_tags: list[ProxyTag] = Field(
        default_factory=list,
        description='the tags of the member',
        max_length=15)
    userproxy: UserProxy | None = Field(
        None,
        description='the userproxy of the member')
    simplyplural_id: str | None = Field(
        None,
        description='the simplyplural id of the member'
    )

    @property
    def avatar_url(self) -> str | None:
        return env.avatar_url.format(
            parent_id=self.id,
            hash=self.avatar
        ) if self.avatar else None

    def get_display_name(
        self,
        usergroup: Usergroup,
        group: Group,
        guild: Guild | None,
        userproxy: bool = False
    ) -> str:
        guild = guild or Guild(id=0)

        tag = group.tag or usergroup.config.account_tag

        components = [
            self.name, (
                usergroup.config.tag_format.replace('{tag}', tag)
                if (
                    tag and (
                        (usergroup.userproxy_config.include_tag)
                        if userproxy else
                        (guild.config.force_include_tag or
                         usergroup.config.include_tag))
                ) else ''), (
                usergroup.config.pronoun_format.replace(
                    '{pronouns}', self.pronouns)
                if (
                    self.pronouns and (
                        (usergroup.userproxy_config.include_pronouns)
                        if userproxy else
                        (usergroup.config.include_pronouns)
                    )
                ) else ''
            )
        ]

        return DOUBLESPACE.sub(
            ' ', ' '.join([
                components[index]
                for index in
                usergroup.config.display_name_order
            ]).strip()[:80]
        )

    async def get_group(
        self,
        use_cache: bool = True
    ) -> Group:
        from plural.db.group import Group

        group = await Group.find_one(
            {'members': self.id},
            ignore_cache=not use_cache
        )

        if group is None:
            raise ValueError(f'member {self.id} is not in any group')

        return group

    async def fetch_avatar(
        self,
        session: ClientSession
    ) -> bytes | None:
        if self.avatar is None:
            return None

        async with session.get(self.avatar_url) as response:
            return await response.read()
