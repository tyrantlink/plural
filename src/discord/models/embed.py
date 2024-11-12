from __future__ import annotations
from .base import RawBaseModel
from datetime import datetime


class EmbedFooter(RawBaseModel):
    text: str
    icon_url: str | None = None
    proxy_icon_url: str | None = None


class EmbedImage(RawBaseModel):
    url: str
    proxy_url: str | None = None
    height: int | None = None
    width: int | None = None


class EmbedThumbnail(RawBaseModel):
    url: str
    proxy_url: str | None = None
    height: int | None = None
    width: int | None = None


class EmbedVideo(RawBaseModel):
    url: str | None = None
    proxy_url: str | None = None
    height: int | None = None
    width: int | None = None


class EmbedProvider(RawBaseModel):
    name: str | None = None
    url: str | None = None


class EmbedAuthor(RawBaseModel):
    name: str
    url: str | None = None
    icon_url: str | None = None
    proxy_icon_url: str | None = None


class EmbedField(RawBaseModel):
    name: str
    value: str
    inline: bool | None = None


class Embed(RawBaseModel):
    title: str | None = None
    type: str | None = None
    description: str | None = None
    url: str | None = None
    timestamp: datetime | None = None
    color: int | None = None
    footer: EmbedFooter | None = None
    image: EmbedImage | None = None
    thumbnail: EmbedThumbnail | None = None
    video: EmbedVideo | None = None
    provider: EmbedProvider | None = None
    author: EmbedAuthor | None = None
    fields: list[EmbedField] | None = None

    @classmethod
    def success(cls, message: str, title: str = 'success!') -> Embed:
        return cls(
            title=title,
            description=message,
            color=0x69ff69
        )

    @classmethod
    def error(cls, message: str, title: str = 'error!') -> Embed:
        return cls(
            title=title,
            description=message,
            color=0xff6969
        )
