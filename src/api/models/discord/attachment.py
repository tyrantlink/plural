from pydantic import BaseModel


class Attachment(BaseModel):
    id: str | int
    filename: str | None = None
    title: str | None = None
    description: str | None = None
    content_type: str | None = None
    size: int | None = None
    url: str | None = None
    proxy_url: str | None = None
    height: int | None = None
    width: int | None = None
    ephemeral: bool | None = None
    duration_secs: float | None = None
    waveform: str | None = None
    flags: int | None = None
    # ? not documented in discord api
    placeholder: str | None = None
    placeholder_version: int | None = None
