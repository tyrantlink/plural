from enum import Enum


class ImageExtension(Enum):
    PNG = 0
    JPG = 1
    JPEG = 1
    GIF = 2
    WEBP = 3


class CacheType(Enum):
    GUILD = 0
    ROLE = 1
    CHANNEL = 2
    EMOJI = 3
    WEBHOOK = 4
    MESSAGE = 5
    USER = 6
    MEMBER = 7
