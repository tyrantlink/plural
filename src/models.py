from enum import StrEnum, Enum
from pydantic import BaseModel
from base64 import b64decode
from tomllib import loads


LEGACY_FOOTER = 'userproxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
USERPROXY_FOOTER = '\n\na plural proxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
USERPROXY_FOOTER_LIMIT = 400 - len(USERPROXY_FOOTER.format(username='*' * 32))


class Project(BaseModel):
    class Images(BaseModel):
        base_url: str
        account_id: str
        token: str

    bot_token: str
    bot_public_key: str
    mongo_uri: str
    base_url: str
    api_url: str
    import_proxy_channel_id: int
    error_webhook: str
    gateway_key: str
    logfire_token: str
    dev_environment: bool = True
    images: Images

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


class APIResponse(StrEnum):
    ...  # ? do this later


with open('project.toml', 'r') as f:
    project = Project.model_validate(loads(f.read()))
