from __future__ import annotations

from typing import Any
from re import sub, IGNORECASE

from pydantic import BaseModel, model_validator
from aredis_om import Field

from .redis import BaseRedisModel


class ProxyMember(BaseRedisModel):
    class Meta:
        model_key_prefix = 'member'

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

        prefix: str = Field(
            '',
            max_length=50,
            description='tag must have a prefix or suffix')
        suffix: str = Field(
            '',
            max_length=50,
            description='tag must have a prefix or suffix')
        regex: bool = False
        case_sensitive: bool = False

        @model_validator(mode='after')
        def check_prefix_and_suffix(self) -> ProxyMember.ProxyTag:
            if not self.prefix and not self.suffix:
                raise ValueError(
                    'At least one of prefix or suffix must be non-empty')

            return self

    class UserProxy(BaseRedisModel):
        class Meta:
            embedded = True
        bot_id: str = Field(
            index=True,
            description='bot id')
        public_key: str = Field(description='the userproxy public key')
        token: str = Field(
            description='the bot token')
        command: str = Field(
            'proxy', description='name of the proxy command')
        include_group_tag: bool = Field(
            False, description='whether to include group tags in the bot name')
        attachment_count: int = Field(
            1, description='the number of attachments options to include on the proxy command')
        self_hosted: bool = Field(
            False, description='whether the userproxy is self-hosted')
        guilds: list[str] = Field(
            default_factory=list,
            description='guilds the userproxy is enabled in')

    name: str = Field(
        description='the name of the member',
        min_length=1, max_length=80
    )
    avatar: str | None = Field(
        None,
        description='the avatar uuid of the member; overrides the group avatar'
    )
    proxy_tags: list[ProxyTag] = Field(
        [],
        description='proxy tags for the member',
        max_length=15
    )
    userproxy: ProxyMember.UserProxy | None = Field(
        None,
        description='the userproxy information'
    )
    sp_id: str | None = Field(
        None,
        description='the simply plural system id of the member'
    )
