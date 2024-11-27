from src.discord.types import Snowflake, MISSING, MissingOr, MissingNoneOr
from src.discord.http import File, get_from_cdn
from .enums import AttachmentFlag
from .base import RawBaseModel
from io import BytesIO


class Attachment(RawBaseModel):
    id: Snowflake
    filename: str
    title: MissingOr[str] = MISSING
    description: MissingOr[str] = MISSING
    content_type: MissingOr[str] = MISSING
    size: int
    url: str
    proxy_url: str
    height: MissingNoneOr[int] = MISSING
    width: MissingNoneOr[int] = MISSING
    ephemeral: MissingOr[bool] = MISSING
    duration_secs: MissingOr[float] = MISSING
    waveform: MissingOr[str] = MISSING
    flags: MissingOr[AttachmentFlag] = MISSING

    @property
    def spoiler(self) -> bool:
        return self.filename.startswith('SPOILER_')

    async def read(self) -> bytes:
        return await get_from_cdn(self.url)

    async def as_file(self) -> File:
        return File(
            BytesIO(await self.read()),
            filename=self.filename,
            description=self.description or None,
            spoiler=self.spoiler,
            duration_secs=self.duration_secs or None,
            waveform=self.waveform or None
        )
