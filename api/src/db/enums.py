from enum import Enum, StrEnum


__all__ = (
    'ImageExtension',
    'ReplyFormat',
    'ReplyType',
    'SupporterTier',
    'ProxyReason'
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
    REPLY = 1


class SupporterTier(Enum):
    NONE = 0
    DEVELOPER = 1
    SUPPORTER = 2


class ProxyReason(StrEnum):
    NONE = 'no reason given, this should never be seen'
    USERPROXY = 'userproxy message'
    PROXY_TAGS = 'matched proxy tags {prefix}text{suffix}'
    GLOBAL_AUTOPROXY = 'global autoproxy'
    GUILD_AUTOPROXY = 'server autoproxy'


class AutoProxyMode(Enum):
    LATCH = 0
    FRONT = 1
