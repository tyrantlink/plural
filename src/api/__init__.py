

# ? images are stored in mongodb as binary data, and accessed through the api, and cached on cloudflare and discord
from fastapi import FastAPI
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.project import project
    from src.db import MongoDatabase
    DB = MongoDatabase(project.mongo_uri)

    await DB.connect()

    from .routers import image, message
    app.include_router(image.router)
    app.include_router(message.router)

    yield


app = FastAPI(
    title="/plu/ral API",
    lifespan=lifespan,
    version="0.1.0"
)


@app.get("/")
async def root():
    return {'message': 'this is very basic i\'ll work on it later'}
