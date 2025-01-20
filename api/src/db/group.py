from re import sub, IGNORECASE
from typing import Any

from pydantic import model_validator
from aredis_om import Field

from .redis import BaseRedisModel, RedisPK


class Group(BaseRedisModel):
    class Meta:
        model_key_prefix = 'group'

    @model_validator(mode='before')
    @classmethod
    def _handle_clyde(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        if (tag := values.get('tag')) is None:
            return values

        # ? just stolen from pluralkit https://github.com/PluralKit/PluralKit/blob/214a6d5a4933b975068b0272c98d178a47b487d5/src/pluralkit/bot/proxy.py#L62
        values['tag'] = sub(
            '(c)(lyde)',
            '\\1\u200A\\2',
            tag,
            flags=IGNORECASE
        )
        return values

    name: str = Field(
        description='the name of the group',
        min_length=1, max_length=45)
    accounts: set[str] = Field(
        default_factory=set, index=True,
        description='the discord accounts attached to this group'
    )
    avatar: str | None = Field(
        None,
        description='the avatar uuid of the group'
    )
    channels: set[str] = Field(
        default_factory=set,
        description='the discord channels this group is restricted to'
    )
    tag: str | None = Field(
        None,
        max_length=79,
        description='''
        group tag, displayed at the end of the member name
        for example, if a member has the name 'steve' and the tag is '| the skibidi rizzlers',
        the member's name will be displayed as 'steve | the skibidi rizzlers'
        warning: the total max length of a webhook name is 80 characters
        make sure that the name and tag combined are less than 80 characters
        '''.strip().replace('    ', '')
    )
    members: set[RedisPK] = Field(
        default_factory=set,
        description='the members of the group'
    )
