from pydantic import BaseModel


class PartialGuild(BaseModel):
    id: str
    locale: str | None = None
    features: list[str] | None = None

    @property
    def upload_limit(self) -> int:
        _features = self.features or []
        return (
            1024*1024*100
            if 'ANIMATED_BANNER' in _features
            else 1024*1024*50
            if 'BANNER' in _features
            else 1024*1024*25
        )
