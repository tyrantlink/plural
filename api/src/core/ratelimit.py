from collections.abc import Callable
from datetime import timedelta
from typing import NamedTuple
from time import time


class RateLimitResponse(NamedTuple):
    block: bool
    limit: int
    remaining: int
    retry_after: int
    reset: int

    def as_headers(self) -> dict[str, str]:
        headers = {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(self.remaining),
            'X-RateLimit-Reset': str(self.reset)
        }

        if self.block:
            headers['Retry-After'] = str(self.retry_after)

        return headers


RATELIMITS: dict[
    Callable,
    tuple[int, int]
] = {}


def ratelimit(limit: int, interval: timedelta) -> Callable:
    def decorator(function: Callable) -> Callable:
        RATELIMITS[function] = (limit, int(interval.total_seconds()))
        return function

    return decorator


async def ratelimit_check(
    key: str,
    function: Callable
) -> RateLimitResponse | None:
    from plural.db import redis

    if function not in RATELIMITS:
        return None

    limit, interval = RATELIMITS.get(function)

    response = await redis.execute_command(
        'CL.THROTTLE',
        f'ratelimit:{key}:{function.__name__}',
        limit-1,
        limit,
        interval
    )

    return RateLimitResponse(
        block=response[0] == 1,
        limit=response[1],
        remaining=response[2],
        retry_after=response[3],
        reset=int(time()+response[4])
    )
