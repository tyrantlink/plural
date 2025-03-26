from enum import Enum

from fastapi.responses import Response
from fastapi import APIRouter, Depends

from plural.db import redis

from src.core.auth import internal_key_validator


router = APIRouter(include_in_schema=False)


class ValidRedisCommand(str, Enum):
    SISMEMBER = 'SISMEMBER'
    SADD = 'SADD'
    SREM = 'SREM'
    SCARD = 'SCARD'


@router.post(
    '/__redis/{command}/{key}/{value}',
    dependencies=[Depends(internal_key_validator)])
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
