from fastapi import FastAPI, Response, Request, WebSocket
from logging import getLogger, Filter, LogRecord
from contextlib import asynccontextmanager
from src.docs import root as docs
from src.version import VERSION
from src.models import project
from typing import Any
import logfire


class LocalHealthcheckFilter(Filter):
    def filter(self, record: LogRecord) -> bool:
        return not bool(
            isinstance(record.args, tuple) and
            len(record.args) == 5 and
            all((
                str(record.args[0]).startswith('172'),
                record.args[1] == 'GET',
                record.args[2] == '/healthcheck',
                record.args[4] == 204
            ))
        )


getLogger("uvicorn.access").addFilter(LocalHealthcheckFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.models import project
    from src.db import MongoDatabase
    from .session import session

    DB = MongoDatabase(project.mongo_uri)

    await DB.connect()

    # ? start running bot code
    import src.logic
    import src.commands
    from src.discord.commands import sync_commands

    await sync_commands()

    from src.routers import discord, message  # , member, latch, image, group
    app.include_router(discord.router)
    #! non-discord routes need to be rewritten, i'll do it later
    app.include_router(message.router)
    # app.include_router(member.router)
    # app.include_router(latch.router)
    # app.include_router(image.router)
    # app.include_router(group.router)

    yield

    await session.close()
    logfire.info('shutting down')
    logfire.shutdown()


app = FastAPI(
    title='/plu/ral API',
    description='get an API key by running /api on the bot',
    lifespan=lifespan,
    docs_url='/swdocs',
    redoc_url='/docs',
    version=VERSION,
    debug=project.dev_environment
)


def live_discord_redaction(request: Request | WebSocket, attributes: dict[str, Any]) -> dict[str, Any] | None:
    if project.dev_environment:
        return attributes

    match request.url.path:
        # ? might do more later
        case '/discord/event' | '/discord/interaction':
            return None

    return attributes


if project.logfire_token:
    logfire.configure(
        service_name='/plu/ral' + ('-dev' if project.dev_environment else ''),
        service_version=VERSION,
        token=project.logfire_token,
        environment='development' if project.dev_environment else 'production',
        scrubbing=False if project.dev_environment else None,
        console=False
    )
    logfire.instrument_pymongo(
        capture_statement=True
    )
    logfire.instrument_aiohttp_client()
    logfire.instrument_system_metrics()
    logfire.instrument_fastapi(
        app,
        capture_headers=app.debug,
        request_attributes_mapper=live_discord_redaction,
        excluded_urls=['/healthcheck']
    )


@app.middleware("http")
async def set_client_ip(request: Request, call_next):
    client_ip = request.headers.get('CF-Connecting-IP')

    if client_ip and request.client is not None:
        request.scope['client'] = (client_ip, request.scope['client'][1])

    return await call_next(request)


@app.get(
    '/',
    responses=docs.get__root)
async def get__root():
    return {'message': 'this is very basic i\'ll work on it later', 'version': VERSION}


@app.get(
    '/healthcheck',
    status_code=204,
    include_in_schema=False)
async def get__healthcheck():
    return Response(status_code=204)
