from collections.abc import AsyncGenerator, Callable, Awaitable
from fastapi import FastAPI, Response, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from src.core.models import env, INSTANCE
from contextlib import asynccontextmanager
from src.core.version import VERSION
from typing import Any
import logfire


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from src.db import redis_init
    # from .session import session

    await redis_init(env.redis_url)

    # # ? start running bot code
    # import src.logic
    # import src.commands  # noqa: F401
    # from src.discord.commands import sync_commands

    logfire.info('started on instance {instance_id}', instance_id=INSTANCE)

    # await sync_commands()

    from src.routers import autoproxy, discord, message, migration
    app.include_router(autoproxy.router)
    app.include_router(discord.router)
    app.include_router(message.router)
    app.include_router(migration.router)

    yield

    # await session.close()
    logfire.info('shutting down')
    logfire.shutdown()


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


def live_discord_redaction(request: Request | WebSocket, attributes: dict[str, Any]) -> dict[str, Any] | None:
    if env.dev:
        return attributes

    match request.url.path:
        # ? might do more later
        case '/discord/event' | '/discord/interaction':
            return None

    return attributes


if env.logfire_token:
    logfire.configure(
        service_name='/plu/ral' + ('-dev' if env.dev else ''),
        service_version=VERSION,
        token=env.logfire_token,
        environment='development' if env.dev else 'production',
        scrubbing=False if env.dev else None,
        console=False,
        metrics=False
    )


@app.middleware("http")
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
        'message': '/plu/ral api, you should ',
        'instance': INSTANCE,
        'version': VERSION
    }


@app.get(
    '/healthcheck',
    status_code=204,
    include_in_schema=False)
async def get__healthcheck() -> Response:
    return Response(status_code=204)
