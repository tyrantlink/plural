from pydantic import BaseModel
from tomllib import loads
from enum import StrEnum


class Project(BaseModel):
    bot_token: str
    mongo_uri: str
    base_url: str
    import_proxy_channel_id: int


class DebugMessage(StrEnum):
    ENABLER = 'starting message debug on message'  # ? gets stripped out of message
    AUTHOR_BOT = 'message author was a bot, skipping proxy'
    NOT_IN_GUILD = 'message was not in a guild, skipping proxy'
    NO_CONTENT = 'message had no content or attachments, skipping proxy'
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


with open('project.toml', 'r') as f:
    project = Project.model_validate(loads(f.read()))
