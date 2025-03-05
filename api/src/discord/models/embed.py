from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel
from plural.missing import MISSING
from plural.otel import cx

if TYPE_CHECKING:
    from datetime import datetime

    from plural.missing import Optional

    from src.discord.enums import EmbedType


__all__ = (
    'Embed',
)


class Embed(RawBaseModel):
    class Footer(RawBaseModel):
        text: str
        """footer text"""
        icon_url: Optional[str]
        """url of footer icon (only supports http(s) and attachments)"""
        proxy_icon_url: Optional[str]
        """a proxied url of footer icon"""

    class Image(RawBaseModel):
        url: str
        """source url of image (only supports http(s) and attachments)"""
        proxy_url: Optional[str]
        """a proxied url of the image"""
        height: Optional[int]
        """height of image"""
        width: Optional[int]
        """width of image"""

    class Thumbnail(RawBaseModel):
        url: str
        """source url of thumbnail (only supports http(s) and attachments)"""
        proxy_url: Optional[str]
        """a proxied url of the thumbnail"""
        height: Optional[int]
        """height of thumbnail"""
        width: Optional[int]
        """width of thumbnail"""

    class Video(RawBaseModel):
        url: Optional[str]
        """source url of video"""
        proxy_url: Optional[str]
        """a proxied url of the video"""
        height: Optional[int]
        """height of video"""
        width: Optional[int]
        """width of video"""

    class Provider(RawBaseModel):
        name: Optional[str]
        """name of provider"""
        url: Optional[str]
        """url of provider"""

    class Author(RawBaseModel):
        name: str
        """name of author"""
        url: Optional[str]
        """url of author (only supports http(s))"""
        icon_url: Optional[str]
        """url of author icon (only supports http(s) and attachments)"""
        proxy_icon_url: Optional[str]
        """a proxied url of author icon"""

    class Field(RawBaseModel):
        name: str
        """name of the field"""
        value: str
        """value of the field"""
        inline: Optional[bool]
        """whether or not this field should display inline"""

    title: Optional[str]
    """title of embed"""
    type: Optional[EmbedType]
    """type of embed (always "rich" for webhook embeds)"""
    description: Optional[str]
    """description of embed"""
    url: Optional[str]
    """url of embed"""
    timestamp: Optional[datetime]
    """timestamp of embed content"""
    color: Optional[int]
    """color code of the embed"""
    footer: Optional[Embed.Footer]
    """footer information"""
    image: Optional[Embed.Image]
    """image information"""
    thumbnail: Optional[Embed.Thumbnail]
    """thumbnail information"""
    video: Optional[Embed.Video]
    """video information"""
    provider: Optional[Embed.Provider]
    """provider information"""
    author: Optional[Embed.Author]
    """author information"""
    fields: Optional[list[Embed.Field]]
    """fields information, max of 25"""

    @classmethod
    def success(
        cls,
        message: str,
        title: str = 'Success!',
        insert_command_ref: bool = False
    ) -> Embed:
        from src.discord.commands import insert_cmd_ref
        return cls(
            title=title,
            description=(
                insert_cmd_ref(message)
                if insert_command_ref else
                message),
            color=0x69ff69
        )

    @classmethod
    def warning(
        cls,
        message: str,
        title: str = 'Warning!',
        insert_command_ref: bool = False
    ) -> Embed:
        from src.discord.commands import insert_cmd_ref
        return cls(
            title=title,
            description=(
                insert_cmd_ref(message)
                if insert_command_ref else
                message),
            color=0xffff69
        )

    @classmethod
    def error(
        cls,
        message: str,
        title: str = 'Error!',
        expected: bool = True,
        insert_command_ref: bool = True
    ) -> Embed:
        from src.discord.commands import insert_cmd_ref
        embed = cls(
            title=title,
            description=(
                insert_cmd_ref(message)
                if insert_command_ref else
                message),
            color=0xff6969
        )

        if not expected:
            embed.set_footer(
                f'error id: {cx().context.span_id:x}'
            )

        return embed

    def add_field(
        self,
        name: str,
        value: str,
        inline: bool = True,
        insert_command_ref: bool = False
    ) -> Embed:
        from src.discord.commands import insert_cmd_ref

        self.fields = self.fields or []
        self.fields.append(Embed.Field(
            name=name,
            value=(
                insert_cmd_ref(value)
                if insert_command_ref else
                value),
            inline=inline
        ))

        return self

    def set_footer(
        self,
        text: str,
        icon_url: Optional[str] = MISSING
    ) -> Embed:
        self.footer = Embed.Footer(text=text, icon_url=icon_url)
        return self

    def set_image(
        self,
        url: str
    ) -> Embed:
        self.image = Embed.Image(url=url)
        return self

    def set_thumbnail(
        self,
        url: str
    ) -> Embed:
        self.thumbnail = Embed.Thumbnail(url=url)
        return self

    def set_author(
        self,
        name: str,
        url: Optional[str] = MISSING,
        icon_url: Optional[str] = MISSING
    ) -> Embed:
        self.author = Embed.Author(name=name, url=url, icon_url=icon_url)
        return self
