from __future__ import annotations
from pydantic import GetJsonSchemaHandler, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from pydantic.json_schema import JsonSchemaValue
from typing import TypeVar, Union, Any, Literal
from enum import StrEnum, Enum
from pydantic import BaseModel
from base64 import b64decode
from tomllib import loads


LEGACY_FOOTERS = {
    'userproxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural',
    'a plural proxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
}
USERPROXY_FOOTER = '\n\na plural proxy for @{username} powered by /plu/ral\nhttps://plural.gg'
USERPROXY_FOOTER_LIMIT = 400 - len(USERPROXY_FOOTER.format(username='*' * 32))


class Project(BaseModel):
    bot_token: str
    bot_public_key: str
    mongo_uri: str
    base_url: str
    api_url: str
    cdn_url: str
    import_proxy_channel_id: int
    error_webhook: str
    gateway_key: str
    logfire_token: str
    cdn_api_key: str
    dev_environment: bool = True

    @property
    def application_id(self) -> int:
        return int(
            b64decode(
                project.bot_token.split('.')[0] + '=='
            ).decode()
        )


class MemberUpdateType(Enum):
    NAME = 0
    AVATAR = 1
    COMMAND = 2
    BIO = 3
    GUILDS = 4


class DebugMessage(StrEnum):
    ENABLER = 'starting message debug on message'  # ? gets stripped out of message
    AUTHOR_BOT = 'message author was a bot, skipping proxy'
    NOT_IN_GUILD = 'message was not in a guild, skipping proxy'
    NO_CONTENT = 'message had no content, attachments, stickers, or polls, skipping proxy'
    AUTOPROXY_BYPASSED = 'latch enabled and message started with backslash, skipping proxy'
    OVER_TEXT_LIMIT = 'message was over 1980 characters, this cannot be proxied due to discord limitations'
    OVER_FILE_LIMIT = 'attachments were above the file size limit, this cannot be proxied due to discord limitations'
    GROUP_CHANNEL_RESTRICTED = 'group `{}` restricted to other channels, skipping proxy'
    AUTHOR_NO_TAGS = 'no proxy tags found for message author, skipping proxy'
    AUTHOR_NO_TAGS_NO_LATCH = 'no proxy tags found for message author and latch is disabled, skipping proxy'
    PERM_SEND_MESSAGES = 'the bot does not have permission to send messages in the current channel, unable to proxy'
    PERM_MANAGE_MESSAGES = 'the bot does not have permission to manage messages in the current channel, unable to proxy'
    PERM_MANAGE_WEBHOOKS = 'the bot does not have permission to manage webhooks in the current channel, unable to proxy'
    PERM_VIEW_CHANNEL = 'the bot does not have permission to view the current channel, unable to proxy'
    PARENT_CHANNEL_FORBIDDEN = 'the bot does not have permission to view the parent channel (or category), unable to proxy'
    SUCCESS = 'would have successfully proxied message, no errors found'
    ATTACHMENTS_AND_STICKERS = 'message had attachments and stickers, skipping proxy'
    INCOMPATIBLE_STICKERS = 'message had incompatible stickers, skipping proxy'
    MATCHED_FROM_TAGS = 'matched from member proxy tags:\n{}text{}'
    MATCHED_FROM_LATCH_GUILD = 'matched from server autoproxy'
    MATCHED_FROM_LATCH_GLOBAL = 'matched from global autoproxy'
    NOT_IN_REFERENCE_CHANNEL = 'the bot does not have permission to view the channel of the forwarded message, unable to proxy'
    PERM_VIEW_CHANNEL_REFERENCE = 'the bot does not have permission to view the channel of the forwarded message, unable to proxy'


class APIResponse(StrEnum):
    ...  # ? do this later


class _MissingType:
    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "MISSING"

    def __copy__(self) -> _MissingType:
        return self

    def __deepcopy__(self, _: Any) -> _MissingType:
        return self

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.none_schema(),
            python_schema=core_schema.is_instance_schema(cls),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "null"}


MISSING = _MissingType()

INSTANCE = hex(id(MISSING))[2:]

T = TypeVar('T')
MissingOr = Union[T, _MissingType]
MissingNoneOr = Union[T, None, _MissingType]


with open('project.toml', 'r') as f:
    project = Project.model_validate(loads(f.read()))
