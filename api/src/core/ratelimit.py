from collections.abc import Callable
from datetime import timedelta
from typing import NamedTuple
from hashlib import sha256
from time import time


class RateLimit(NamedTuple):
    limit: int
    interval: int
    keys: list[str]


class RateLimitResponse(NamedTuple):
    block: bool
    limit: int
    remaining: int
    retry_after: int
    reset: int
    bucket: str

    def as_headers(self) -> dict[str, str]:
        headers = {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(self.remaining),
            'X-RateLimit-Reset': str(self.reset),
            'X-RateLimit-Reset-After': f'{self.reset - time():.3f}',
            'X-RateLimit-Bucket': self.bucket
        }

        if self.block:
            headers['Retry-After'] = str(self.retry_after)

        return headers


RATELIMITS: dict[
    tuple[Callable, bool],
    RateLimit
] = {}


def ratelimit(
    limit: int,
    interval: timedelta,
    keys: list[str] | None = None,
    auth: bool = True
) -> Callable:
    def decorator(function: Callable) -> Callable:
        RATELIMITS[(function, auth)] = RateLimit(
            limit,
            int(interval.total_seconds()),
            keys or [])
        return function

    return decorator


async def ratelimit_check(
    key: str,
    function: Callable,
    params: dict[str, str],
    auth: bool
) -> RateLimitResponse | None:
    from plural.db import redis

    if (function, auth) not in RATELIMITS:
        return None

    limit = RATELIMITS.get((function, auth))

    keys = ':'.join([
        value
        for key, value in params.items()
        if key in limit.keys
    ])

    base_key, bucket = (
        f'ratelimit:{key}:',
        sha256(
            f'{function.__name__}:{int(auth)}:{keys}'.encode()
        ).hexdigest()[:32]
    )

    response = await redis.execute_command(
        'CL.THROTTLE',
        base_key + bucket,
        limit.limit - 1,
        limit.limit,
        limit.interval
    )

    return RateLimitResponse(
        block=response[0] == 1,
        limit=response[1],
        remaining=response[2],
        retry_after=response[3],
        reset=int(time() + response[4]),
        bucket=bucket
    )
