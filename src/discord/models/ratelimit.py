from .base import RawBaseModel


class RateLimitResponse(RawBaseModel):
    message: str
    retry_after: float
    global_rate_limit: bool
    code: int | None = None
