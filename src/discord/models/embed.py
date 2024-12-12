from __future__ import annotations
from typing import TYPE_CHECKING
from .base import RawBaseModel


if TYPE_CHECKING:
    from .message import Message
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
    def warning(cls, message: str, title: str = 'warning!') -> Embed:
        return cls(
            title=title,
            description=message,
            color=0xffff69
        )

    @classmethod
    def error(cls, message: str, title: str = 'error!', expected: bool = True) -> Embed:
        embed = cls(
            title=title,
            description=message,
            color=0xff6969
        )

        if not expected:
            embed.set_footer('this error has been automatically reported')

        return embed

    @classmethod
    def reply(cls, message: Message) -> Embed:
        assert message.author is not None

        content = (message.content or '').replace('\n', ' ')

        fcontent = (
            content
            if len(content) <= 75 else
            f'{content[:75].strip()}…'
        )

        jump_url = message.jump_url

        return cls(
            author=EmbedAuthor(
                name=f'{message.author.display_name} ↩️',
                icon_url=message.author.avatar_url),
            color=0x7289da,
            description=(
                f'{'✉️ ' if message.attachments else ''}**[Reply to:]({jump_url})** {fcontent}'
                if fcontent.strip() else
                f'*[click to see attachment{"" if len(message.attachments)-1 else "s"}]({jump_url})*'
                if message.attachments else
                f'*[click to see message]({jump_url})*'
            )
        )

    def add_field(self, name: str, value: str, inline: bool = True) -> Embed:
        self.fields = self.fields or []
        self.fields.append(EmbedField(name=name, value=value, inline=inline))
        return self

    def set_footer(self, text: str, icon_url: str | None = None) -> Embed:
        self.footer = EmbedFooter(text=text, icon_url=icon_url)
        return self

    def set_image(self, url: str) -> Embed:
        self.image = EmbedImage(url=url)
        return self

    def set_thumbnail(self, url: str) -> Embed:
        self.thumbnail = EmbedThumbnail(url=url)
        return self

    def set_author(self, name: str, url: str | None = None, icon_url: str | None = None) -> Embed:
        self.author = EmbedAuthor(name=name, url=url, icon_url=icon_url)
        return self
