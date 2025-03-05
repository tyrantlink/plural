from __future__ import annotations

from typing import TYPE_CHECKING
from base64 import b64encode
from io import BytesIO

from plural.errors import PluralException

from src.core.http import File, GENERAL_SESSION

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from plural.missing import Optional, Nullable

    from src.discord.enums import AttachmentFlag
    from src.discord.types import Snowflake


__all__ = (
    'Attachment',
)


class Attachment(RawBaseModel):
    id: Snowflake
    """attachment id"""
    filename: str
    """name of file attached"""
    title: Optional[str]
    """the title of the file"""
    description: Optional[str]
    """description for the file (max 1024 characters)"""
    content_type: Optional[str]
    """the attachment's media type"""
    size: int
    """size of file in bytes"""
    url: str
    """source url of file"""
    proxy_url: str
    """a proxied url of file"""
    height: Optional[Nullable[int]]
    """height of file (if image)"""
    width: Optional[Nullable[int]]
    """width of file (if image)"""
    ephemeral: Optional[bool]
    """whether this attachment is ephemeral\n\nEphemeral attachments will automatically be removed after a set period of time. Ephemeral attachments on messages are guaranteed to be available as long as the message itself exists."""
    duration_secs: Optional[float]
    """the duration of the audio file (currently for voice messages)"""
    waveform: Optional[str]
    """base64 encoded bytearray representing a sampled waveform (currently for voice messages)"""
    flags: Optional[AttachmentFlag]
    """attachment flags combined as a bitfield* (AttachmentFlag enum)"""

    @property
    def spoiler(self) -> bool:
        return self.filename.startswith('SPOILER_')

    async def read(self, limit: int | None = None) -> bytes:
        async with GENERAL_SESSION.get(self.url) as response:
            if limit is None:
                return await response.read()

            data = bytearray()

            async for chunk in response.content.iter_chunked(16384):
                data.extend(chunk)

                if len(data) > limit:
                    raise PluralException(
                        f'attachment `{self.filename}` too large'
                    )

        return bytes(data)

    async def to_file(self) -> File:
        return File(
            BytesIO(await self.read()),
            filename=self.filename,
            description=self.description or None,
            spoiler=self.spoiler,
            duration_secs=self.duration_secs or None,
            waveform=self.waveform or None
        )

    async def to_image_data(self, limit: int | None = None) -> str:
        return (
            f'data:{self.content_type};base64,'
            f'{b64encode(await self.read(limit)).decode('ascii')}'
        )
