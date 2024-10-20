from contextlib import asynccontextmanager
from src.api.drest import start_drest
from src.api.docs import root as docs
from fastapi import FastAPI, Response


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.models import project
    from src.db import MongoDatabase
    DB = MongoDatabase(project.mongo_uri)

    await DB.connect()
    await start_drest()
    from src.api.drest import drest_client

    from .routers import image, message, latch, member, group, userproxy
    app.include_router(userproxy.router)
    app.include_router(message.router)
    app.include_router(member.router)
    app.include_router(latch.router)
    app.include_router(image.router)
    app.include_router(group.router)

    yield

    await drest_client.close()
    from src.api.drest import drest_app
    await drest_app.close()


app = FastAPI(
    title='/plu/ral API',
    description='get an API key by running /api on the bot',
    lifespan=lifespan,
    docs_url='/swdocs',
    redoc_url='/docs',
    version="1.0.0"
)


@app.get(
    '/',
    responses=docs.get__root)
async def get__root():
    return {'message': 'this is very basic i\'ll work on it later'}


@app.get(
    '/healthcheck',
    status_code=204)
async def get__healthcheck():
    return Response(status_code=204)
