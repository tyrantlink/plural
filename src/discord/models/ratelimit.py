from .base import RawBaseModel


__all__ = (
    'RateLimitResponse',
)


class RateLimitResponse(RawBaseModel):
    message: str
    retry_after: float
    global_rate_limit: bool
    code: int | None = None
