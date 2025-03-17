from datetime import datetime, UTC

from fastapi.responses import Response
from fastapi import APIRouter

from plural.db import redis, Message


router = APIRouter(prefix='/messages', tags=['Messages'])


def _snowflake_to_age(snowflake: int) -> float:
    return (
        datetime.now(UTC) - datetime.fromtimestamp(
            ((snowflake >> 22) + 1420070400000) / 1000,
            tz=UTC)
    ).total_seconds()


@router.head('/{message_id}')
async def head__message(
    message_id: int
) -> Response:
    if _snowflake_to_age(message_id) > 604_800:  # 7 days
        return Response(status_code=410)

    if _snowflake_to_age(message_id) < -30:
        return Response(status_code=400)

    pending = await redis.exists(f'pending_proxy:{message_id}')

    if pending:
        return Response(status_code=200)

    message = await Message.find_one({'$or': [
        {'original_id': message_id},
        {'proxy_id': message_id}
    ]})

    if message is None:
        return Response(status_code=404)

    return Response(status_code=200)
