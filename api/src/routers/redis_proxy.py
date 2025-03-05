from typing import Annotated
from enum import Enum

from fastapi import APIRouter, Depends, Request, Header, HTTPException
from fastapi.responses import Response

from plural.db import redis

from src.core.models import env


router = APIRouter(include_in_schema=False)


async def redis_key_validator(
    request: Request,  # noqa: ARG001
    authorization: Annotated[str, Header()]
) -> None:
    if authorization != f'Bearer {env.cdn_upload_token}':
        raise HTTPException(status_code=403)


class ValidRedisCommand(str, Enum):
    SISMEMBER = 'SISMEMBER'
    SADD = 'SADD'
    SREM = 'SREM'
    SCARD = 'SCARD'


@router.post(
    '/__redis/{command}/{key}/{value}',
    dependencies=[Depends(redis_key_validator)])
async def post__redis(
    command: ValidRedisCommand,
    key: str,
    value: str | None = None,
) -> Response:
    if not key.startswith('avatar:'):
        return Response(status_code=403)

    if value is None and command != ValidRedisCommand.SCARD:
        return Response(status_code=400)

    match command:
        case ValidRedisCommand.SISMEMBER:
            response = await redis.sismember(key, value)
        case ValidRedisCommand.SADD:
            response = bool(await redis.sadd(key, value))
        case ValidRedisCommand.SREM:
            response = bool(await redis.srem(key, value))
        case ValidRedisCommand.SCARD:
            response = bool(await redis.scard(key))
        case _:
            return Response(status_code=500)

    return Response(status_code=(
        200 if response else 204
    ))
