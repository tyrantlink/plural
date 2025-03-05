from contextlib import suppress
from traceback import print_exc
from time import time_ns

from redis import ResponseError

from plural.db import redis_init, mongo_init
from plural.utils import create_strong_task
from plural.env import INSTANCE
from plural.otel import span


async def event_listener() -> None:
    with span(f'initializing bot instance {INSTANCE}'):
        await redis_init()
        await mongo_init()

    from plural.db import redis

    from .listener import on_event

    with suppress(ResponseError):
        await redis.xgroup_create(
            'discord_events',
            'plural_consumers',
            id='0',
            mkstream=True
        )

    while True:
        try:
            data = await redis.xreadgroup(
                groupname='plural_consumers',
                consumername='plural_worker',
                streams={'discord_events': '>'},
                count=1,
                block=5000,
            )

            if not data:
                continue

            for key, event in data[0][1]:
                await create_strong_task(on_event(key, event['data'], start_time=time_ns()))
        except Exception:  # noqa: BLE001
            print_exc()
