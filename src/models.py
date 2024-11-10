from enum import StrEnum, Enum
from pydantic import BaseModel
from tomllib import loads


USERPROXY_FOOTER = 'userproxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
USERPROXY_FOOTER_LIMIT = 400 - len(USERPROXY_FOOTER.format(username='*' * 32))


class Project(BaseModel):
    bot_token: str
    mongo_uri: str
    base_url: str
    api_url: str
    import_proxy_channel_id: int
    error_webhook: str
    gateway_key: str
    dev_environment: bool = True


class ReplyAttachment(BaseModel):
    id: str
    filename: str
    size: int
    url: str
    proxy_url: str
    height: int | None = None
    width: int | None = None


class MemberUpdateType(Enum):
    NAME = 1
    AVATAR = 2
    DESCRIPTION = 3


class DebugMessage(StrEnum):
    ENABLER = 'starting message debug on message'  # ? gets stripped out of message
    AUTHOR_BOT = 'message author was a bot, skipping proxy'
    NOT_IN_GUILD = 'message was not in a guild, skipping proxy'
    NO_CONTENT = 'message had no content, attachments, stickers, or polls, skipping proxy'
    AUTOPROXY_BYPASSED = 'latch enabled and message started with backslash, skipping proxy'
    OVER_TEXT_LIMIT = 'message was over 1980 characters, this cannot be proxied due to discord limitations'
    OVER_FILE_LIMIT = 'attachments were above the file size limit, this cannot be proxied due to discord limitations'
    GROUP_CHANNEL_RESTRICTED = 'group {} channel restricted to other channels, skipping proxy'
    AUTHOR_NO_TAGS = 'no proxy tags found for message author, skipping proxy'
    AUTHOR_NO_TAGS_NO_LATCH = 'no proxy tags found for message author and latch is disabled, skipping proxy'
    PERM_SEND_MESSAGES = 'the bot does not have permission to send messages in the current channel, unable to proxy'
    PERM_MANAGE_MESSAGES = 'the bot does not have permission to manage messages in the current channel, unable to proxy'
    PERM_MANAGE_WEBHOOKS = 'the bot does not have permission to manage webhooks in the current channel, unable to proxy'
    SUCCESS = 'would have successfully proxied message, no errors found'
    ATTACHMENTS_AND_STICKERS = 'message had attachments and stickers, skipping proxy'
    INCOMPATIBLE_STICKERS = 'message had incompatible stickers, skipping proxy'


class APIResponse(StrEnum):
    ...  # ? do this later


with open('project.toml', 'r') as f:
    project = Project.model_validate(loads(f.read()))
