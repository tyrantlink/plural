from contextlib import asynccontextmanager
from src.api.docs import root as docs
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.models import project
    from src.db import MongoDatabase
    DB = MongoDatabase(project.mongo_uri)

    await DB.connect()

    from .routers import image, message, latch
    app.include_router(image.router)
    app.include_router(message.router)
    app.include_router(latch.router)

    yield


app = FastAPI(
    title="/plu/ral API",
    lifespan=lifespan,
    version="0.1.0"
)


@app.get(
    "/",
    responses=docs.get__root
)
async def root():
    return {'message': 'this is very basic i\'ll work on it later'}
