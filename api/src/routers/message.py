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


@router.head(
    '/{message_id}',
    description="""
        Check if a message was either deleted or created by /plu/ral""",
    responses={
        200: {
            'content': None,
            'description': 'Message found',
            'headers': {
                'Cache-Control': 'public, max-age=604800'
            }},
        404: {
            'content': None,
            'description': 'Message was not found',
            'headers': {
                'Cache-Control': 'public, max-age=604800'
            }},
        410: {
            'content': None,
            'description': 'Message is older than 7 days; status is unknown',
            'headers': {
                'Cache-Control': 'public, max-age=604800'
            }},
        400: {
            'content': None,
            'description': 'Message is in the future; status is unknown'}})
async def head__message(
    message_id: int
) -> Response:
    if _snowflake_to_age(message_id) > 604_800:  # 7 days
        return Response(
            status_code=410,
            headers={'Cache-Control': 'public, max-age=604800'}
        )

    if _snowflake_to_age(message_id) < -30:
        return Response(status_code=400)

    pending = await redis.exists(f'pending_proxy:{message_id}')

    if pending:
        return Response(
            status_code=200,
            headers={'Cache-Control': 'public, max-age=604800'}
        )

    message = await Message.find_one({'$or': [
        {'original_id': message_id},
        {'proxy_id': message_id}
    ]})

    if message is None:
        return Response(
            status_code=404,
            headers={'Cache-Control': 'public, max-age=604800'}
        )

    return Response(
        status_code=200,
        headers={'Cache-Control': 'public, max-age=604800'}
    )
