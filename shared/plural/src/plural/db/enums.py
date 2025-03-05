from enum import Enum, Flag


__all__ = (
    'ImageExtension',
    'ProxyReason',
    'ReplyFormat',
    'ReplyType',
    'SupporterTier',
)


class ImageExtension(Enum):
    PNG = 0
    JPG = 1
    JPEG = 1  # noqa: PIE796
    GIF = 2
    WEBP = 3

    @property
    def mime_type(self) -> str:
        return {
            ImageExtension.PNG: 'image/png',
            ImageExtension.JPG: 'image/jpeg',
            ImageExtension.GIF: 'image/gif',
            ImageExtension.WEBP: 'image/webp'
        }[self]


class ReplyFormat(Enum):
    NONE = 0
    INLINE = 1
    EMBED = 2


class ReplyType(Enum):
    QUEUE = 0
    """Used for userproxy queue for reply option"""
    REPLY = 1
    """Used to store the referenced message when using the reply command"""


class SupporterTier(Enum):
    NONE = 0
    DEVELOPER = 1
    SUPPORTER = 2


class ProxyReason(Enum):
    NONE = 'no reason given, this should never be seen'
    USERPROXY = 'userproxy message'
    PROXY_TAGS = 'matched proxy tags {prefix}text{suffix}'
    GLOBAL_AUTOPROXY = 'global autoproxy'
    GUILD_AUTOPROXY = 'server autoproxy'


class AutoProxyMode(Enum):
    LATCH = 0
    FRONT = 1
    LOCKED = 2


class ApplicationScope(Flag):
    NONE = 0
    LOGGING = 1 << 0
    AUTHORIZE_USERS = 1 << 1
    USER_EVENTS = 1 << 2
    MODIFY_USER_DATA = 1 << 3
    SEND_MESSAGES = 1 << 4  # ? requires approval
    USERPROXY_TOKENS = 1 << 5  # ? requires approval
    SP_TOKENS = 1 << 6  # ? requires approval


class GroupSharePermissionLevel(Enum):
    PROXY_ONLY = 0
    FULL_ACCESS = 1


class ShareType(Enum):
    USERGROUP = 0
    GROUP = 1


class PaginationStyle(Enum):
    BASIC_ARROWS = 0
    TEXT_ARROWS = 1
    REM_AND_RAM = 2
