from enum import Enum


__all__ = (
    'CacheType',
    'ImageExtension',
    'ReplyFormat',
)


class ImageExtension(Enum):
    PNG = 0
    JPG = 1
    JPEG = 1 # noqa: PIE796
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


class CacheType(Enum):
    GUILD = 0
    ROLE = 1
    CHANNEL = 2
    EMOJI = 3
    WEBHOOK = 4
    MESSAGE = 5
    USER = 6
    MEMBER = 7
    ERROR = 8


class ReplyFormat(Enum):
    NONE = 0
    INLINE = 1
    EMBED = 2
