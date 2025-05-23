from collections.abc import AsyncGenerator, Callable, Awaitable
from contextlib import asynccontextmanager
from textwrap import dedent
from asyncio import gather
from random import randint
from typing import Any

from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from starlette.routing import Match
from regex import compile
from orjson import dumps

from plural.db import mongo_init, redis_init
from plural.utils import create_strong_task
from plural.missing import is_not_missing
from plural.env import INSTANCE
from plural.otel import span

from src.core.version import VERSION
from src.core.models import env

from .route import SUPPRESSED_PATHS, ROUTE_NAMES, suppress
from .stupid_openapi_patch import patched_openapi


PATH_PATTERN = compile(
    r'{(.*?)}'
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    with span(f'initializing api instance {INSTANCE}'):
        await env.init()
        await gather(
            mongo_init(),
            redis_init(),
            emoji_init()
        )

        from src.routers import (
            application,
            redis_proxy,
            userproxies,
            autoproxy,
            donation,
            discord,
            message,
            member,
            group,
            user
        )

        # ? commands need to be imported after init
        from src.discord.commands import sync_commands
        import src.commands  # noqa: F401

        await sync_commands(env.bot_token)

        if env.info_bot_token:
            await sync_commands(env.info_bot_token)

        app.include_router(application.router)
        app.include_router(autoproxy.router)
        app.include_router(discord.router)
        app.include_router(donation.router)
        app.include_router(group.router)
        app.include_router(member.router)
        app.include_router(message.router)
        app.include_router(redis_proxy.router)
        app.include_router(user.router)
        app.include_router(userproxies.router)

    create_strong_task(install_count_loop())

    yield

    from src.core.http import DISCORD_SESSION, GENERAL_SESSION
    from src.routers.discord import RUNNING

    if RUNNING:
        print(f'waiting for {len(RUNNING)} tasks to finish...')  # noqa: T201
        await gather(*RUNNING)

    await gather(
        GENERAL_SESSION.close(),
        DISCORD_SESSION.close()
    )


async def install_count_loop() -> None:
    from asyncio import sleep

    from plural.db import redis, Usergroup

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

        users = await Usergroup.count()
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
            'WARNING: Bot is missing the following emojis:\n'
            f'{'\n'.join(EXPECTED)}'
        )


class PatchedFastAPI(FastAPI):
    openapi = patched_openapi


app = PatchedFastAPI(
    title='/plu/ral API',
    description=dedent(f"""
        Get an application token by running `/api` from the bot

        A note about versioning:
        /plu/ral uses [Epoch Semantic Versioning](https://antfu.me/posts/epoch-semver)

        This splits the version into four parts, rather than three:
        - Epoch ({VERSION.split('.')[0]})
          - Incremented on significant architectural changes (basically bumped whenever I want)
        - Major ({VERSION.split('.')[1]})
          - Incremented on breaking changes
        - Minor ({VERSION.split('.')[2]})
          - Incremented on new features
        - Patch ({VERSION.split('.')[3]})
          - Incremented on every commit (bug fixes, documentation changes, etc.)

        When a part is incremented, all parts below are reset to 0.

        For example, if the version is `3.1.2.13` and the major version is incremented,
        the version becomes `3.2.0.0`"""),
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
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
async def ratelimiter(
    request: Request,
    call_next: Callable[..., Awaitable[Any]]
) -> Any:  # noqa: ANN401
    from src.core.ratelimit import ratelimit_check
    from src.core.auth import api_key_validator, selfhosting_key_validator

    if (
        request.headers.get('authorization') ==
        f'Bearer {env.cdn_upload_token}'
    ):
        return await call_next(request)

    for route in app.routes:
        match, data = route.matches(request.scope)

        if match == Match.FULL and isinstance(route, APIRoute):
            break
    else:
        return await call_next(request)

    auth, key = (
        (True, request.headers['Authorization'].split('.')[0].strip())
        if 'Authorization' in request.headers else
        (False, request.scope['client'][0])
    )

    if auth:
        try:
            await (
                selfhosting_key_validator
                if route.path in {'/userproxies'} else
                api_key_validator
            )(request.headers['Authorization'])
        except HTTPException as e:
            return Response(
                dumps(e.detail)
                if isinstance(e.detail, dict) else
                str(e.detail),
                e.status_code,
                e.headers
            )

    limit_response = await ratelimit_check(
        key,
        route.endpoint,
        data.get('path_params', {}),
        auth
    )

    if limit_response and limit_response.block:
        return Response(
            status_code=429,
            headers=limit_response.as_headers()
        )

    response = await call_next(request)

    if limit_response:
        response.headers.update(
            limit_response.as_headers()
        )

    return response


# @app.middleware('http')
# async def cache(
#     request: Request,
#     call_next: Callable[..., Awaitable[Any]]
# ) -> Any:  # noqa: ANN401
#     from src.core.cache import cache_check

#     if (
#         request.headers.get('authorization') ==
#         f'Bearer {env.cdn_upload_token}'
#     ):
#         return await call_next(request)

#     for route in app.routes:
#         match, data = route.matches(request.scope)

#         if match == Match.FULL and isinstance(route, APIRoute):
#             break
#     else:
#         return await call_next(request)

#     auth, key = (
#         (True, request.headers['Authorization'].split('.')[0].strip())
#         if 'Authorization' in request.headers else
#         (False, request.scope['client'][0])
#     )


@app.middleware('http')
async def otel_trace(
    request: Request,
    call_next: Callable[..., Awaitable[Any]]
) -> Any:  # noqa: ANN401
    for route in app.routes:
        match, data = route.matches(request.scope)

        if match == Match.FULL and isinstance(route, APIRoute):
            break
    else:
        return await call_next(request)

    if route.endpoint in SUPPRESSED_PATHS:
        return await call_next(request)

    path = ROUTE_NAMES.get(
        route.endpoint,
        PATH_PATTERN.sub(r':\1', route.path)
    )

    parent = None
    if (
        request.headers.get('authorization') ==
        f'Bearer {env.cdn_upload_token}'
    ):
        parent = request.headers.get('traceparent')

    with span(
        f'{request.method} {path}',
        parent=parent,
        attributes={
            'http.path': request.url.path,
            'http.method': request.method,
            'http.path_params': [
                f'{key}={value}'
                for key, value in data.get('path_params', {}).items()],
            'http.query_params': [
                f'{key}={value}'
                for key, value in dict(request.query_params).items()
            ]
        }
    ) as current_span:
        try:
            response = await call_next(request)
        except:
            current_span.set_attribute('http.status_code', 500)
            raise

        current_span.set_attribute('http.status_code', response.status_code)

    response.headers['x-trace-id'] = f'{current_span.context.trace_id:x}'

    return response


@app.middleware('http')
async def set_client_ip(
    request: Request,
    call_next: Callable[..., Awaitable[Any]]
) -> Any:  # noqa: ANN401
    client_ip = request.headers.get('CF-Connecting-IP')

    if client_ip and request.client is not None:
        request.scope['client'] = (client_ip, request.scope['client'][1])

    return await call_next(request)


@app.get(
    '/',
    include_in_schema=False)
@suppress()
async def get__root(request: Request) -> Response:
    if 'text/html' in request.headers.get('accept', ''):
        return RedirectResponse('/docs', 308)

    return JSONResponse({
        'message': 'Hello from the /plu/ral api!',
        'instance': INSTANCE,
        'version': VERSION
    })


@app.get(
    '/healthcheck',
    status_code=204,
    include_in_schema=False)
@suppress()
async def get__healthcheck() -> Response:
    return Response(status_code=204)


@app.get('/docs', include_in_schema=False)
@suppress()
async def get__docs() -> Response:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title,
        redoc_favicon_url='https://plural.gg/images/icons/favicon-32x32.png'
    )


@app.get('/swdocs', include_in_schema=False)
@suppress()
async def get__swdocs() -> Response:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title,
        swagger_favicon_url='https://plural.gg/images/icons/favicon-32x32.png'
    )
