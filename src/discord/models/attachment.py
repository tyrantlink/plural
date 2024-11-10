from src.discord.http import File, get_from_cdn
from src.discord.types import Snowflake
from .enums import AttachmentFlag
from .base import RawBaseModel
from io import BytesIO

__all__ = ('Attachment',)


class Attachment(RawBaseModel):
    id: Snowflake
    filename: str
    title: str | None = None
    description: str | None = None
    content_type: str
    size: int
    url: str
    proxy_url: str
    height: int | None = None
    width: int | None = None
    ephemeral: bool | None = None
    duration_secs: float | None = None
    waveform: str | None = None
    flags: AttachmentFlag | None = None

    @property
    def spoiler(self) -> bool:
        return self.filename.startswith('SPOILER_')

    async def read(self) -> bytes:
        return await get_from_cdn(self.url)

    async def as_file(self) -> File:
        return File(
            BytesIO(await self.read()),
            filename=self.filename,
            description=self.description,
            spoiler=self.spoiler
        )
