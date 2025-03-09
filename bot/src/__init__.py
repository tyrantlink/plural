from contextlib import suppress
from traceback import print_exc
from time import time_ns

from redis import ResponseError
from aiohttp.web import (
    Application,
    AppRunner,
    Response,
    Request,
    TCPSite
)

from plural.db import redis_init, mongo_init
from plural.utils import create_strong_task
from plural.env import INSTANCE
from plural.otel import span


READY = False


async def event_listener() -> None:
    global READY
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

    READY = True

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


async def healthcheck(
    _request: Request
) -> None:
    global READY
    return Response(status=204 if READY else 503)


async def start_healthcheck() -> None:
    app = Application()
    app.router.add_get('/healthcheck', healthcheck)

    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, '0.0.0.0', 8083)
    await site.start()

    print(  # noqa: T201
        'Healthcheck server started on http://0.0.0.0:8083'
    )
