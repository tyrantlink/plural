from asyncio import Task, gather, create_task, get_event_loop
from collections.abc import Coroutine
from signal import SIGINT, SIGTERM
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
from plural.env import INSTANCE
from plural.otel import span


READY = False
SHUTDOWN = False
RUNNING: set[Task] = set()


def create_strong_task(coroutine: Coroutine) -> Task:
    task = create_task(coroutine)

    RUNNING.add(task)

    task.add_done_callback(RUNNING.discard)

    return task


def shutdown() -> None:
    global SHUTDOWN
    SHUTDOWN = True


async def event_listener() -> None:
    global READY, SHUTDOWN
    with span(f'initializing bot instance {INSTANCE}'):
        await redis_init()
        await mongo_init()

    for signal in (SIGINT, SIGTERM):
        get_event_loop().add_signal_handler(signal, shutdown)

    from plural.db import redis

    from .listener import on_event
    from .logic import emoji_index_init

    await emoji_index_init()

    with suppress(ResponseError):
        await redis.xgroup_create(
            'discord_events',
            'plural_consumers',
            id='0',
            mkstream=True
        )

    READY = True

    while not SHUTDOWN:
        try:
            data = await redis.xreadgroup(
                groupname='plural_consumers',
                consumername='plural_worker',
                streams={'discord_events': '>'},
                count=1,
                block=2500,
            )

            if not data:
                continue

            for key, event in data[0][1]:
                await create_strong_task(on_event(key, event['data'], start_time=time_ns()))
        except ResponseError:
            # ? redis may have restarted and lost the stream
            await redis.xgroup_create(
                'discord_events',
                'plural_consumers',
                id='0',
                mkstream=True)
        except Exception as e:  # noqa: BLE001
            with span('proxy error') as current_span:
                current_span.record_exception(e)
                print_exc()

    if RUNNING:
        print(f'Waiting for {len(RUNNING)} tasks to finish...')  # noqa: T201

    await gather(*RUNNING)

    from src.http import GENERAL_SESSION, DISCORD_SESSION
    await GENERAL_SESSION.close()
    await DISCORD_SESSION.close()


async def healthcheck(
    _request: Request
) -> Response:
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
