from collections.abc import AsyncGenerator, Callable, Awaitable
from contextlib import asynccontextmanager
from asyncio import gather
from random import randint
from typing import Any

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Response, Request

from plural.db import mongo_init, redis_init
from plural.utils import create_strong_task
from plural.missing import is_not_missing
from plural.env import INSTANCE
from plural.otel import span

from src.core.version import VERSION
from src.core.models import env


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    with span(f'initializing api instance {INSTANCE}'):
        await gather(
            env.init(),
            mongo_init(),
            redis_init(),
            emoji_init()
        )

        from src.routers import discord, message, redis_proxy
        # ? commands need to be imported after init
        from src.discord.commands import sync_commands
        import src.commands  # noqa: F401

        await sync_commands(env.bot_token)

        app.include_router(discord.router)
        app.include_router(message.router)
        app.include_router(redis_proxy.router)

    create_strong_task(install_count_loop())

    yield

    from src.core.http import DISCORD_SESSION, GENERAL_SESSION

    await DISCORD_SESSION.close()
    await GENERAL_SESSION.close()


async def install_count_loop() -> None:
    from asyncio import sleep

    from plural.db import redis

    from src.discord.models import Application

    first_run = True

    if await redis.get('discord_users') is None:
        await redis.set('discord_users', 0)

    if await redis.get('discord_guilds') is None:
        await redis.set('discord_guilds', 0)

    last_user_count = int(await redis.get('discord_users'))
    last_guild_count = int(await redis.get('discord_guilds'))

    while True:
        if not first_run:
            await sleep(randint(480, 900))

        first_run = False

        application = await Application.fetch(env.bot_token, silent=True)

        users = application.approximate_user_install_count
        guilds = application.approximate_guild_count

        if (
            (not is_not_missing(users) or users == last_user_count) and
            (not is_not_missing(guilds) or guilds == last_guild_count)
        ):
            continue

        with span(
            f'updated install count to {users} users and {guilds} guilds',
            attributes={
                'users': users,
                'guilds': guilds
            }
        ):
            last_user_count = users
            last_guild_count = guilds
            await redis.set('discord_users', users)
            await redis.set('discord_guilds', guilds)


async def emoji_init() -> None:
    from src.discord.models import Application
    from src.core.emoji import EMOJI, EXPECTED

    with span('initializing application emojis'):
        emojis = await Application.list_emojis(env.bot_token)

        for emoji in emojis:
            if emoji.name not in EXPECTED:
                continue

            EMOJI[emoji.name] = emoji
            EXPECTED.discard(emoji.name)

    if EXPECTED:
        print(  # noqa: T201
            f'WARNING: Bot is missing the following emojis: {'\n'.join(EXPECTED)}'
        )


app = FastAPI(
    title='/plu/ral API',
    description='get an API key by running /api on the bot',
    lifespan=lifespan,
    docs_url='/swdocs',
    redoc_url='/docs',
    version=VERSION,
    debug=env.dev
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*']
)


@app.middleware('http')
async def set_client_ip(
    request: Request,
    call_next: Callable[..., Awaitable[Any]]
) -> Any:  # noqa: ANN401
    client_ip = request.headers.get('CF-Connecting-IP')

    if client_ip and request.client is not None:
        request.scope['client'] = (client_ip, request.scope['client'][1])

    return await call_next(request)


@app.get('/')
async def get__root() -> dict[str, str]:
    return {
        'message': 'hello from the /plu/ral api!',
        'instance': INSTANCE,
        'version': VERSION
    }


@app.get(
    '/healthcheck',
    status_code=204,
    include_in_schema=False)
async def get__healthcheck() -> Response:
    return Response(status_code=204)
