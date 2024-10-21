from pydantic import BaseModel


class PartialGuild(BaseModel):
    id: str
    locale: str | None = None
    features: list[str] | None = None
