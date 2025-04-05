from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Response, Security
from textwrap import dedent
from asyncio import sleep
from orjson import dumps

from plural.db import redis, Message, ProxyMember

from src.core.auth import api_key_validator, TokenData
from src.models import MessageModel, AuthorModel
from src.core.ratelimit import ratelimit
from src.core.route import name

from src.docs import (
    message_response,
    author_response,
    response,
    Example
)


router = APIRouter(prefix='/messages', tags=['Messages'])


def _snowflake_to_age(snowflake: int) -> float:
    return (
        datetime.now(UTC) - datetime.fromtimestamp(
            ((snowflake >> 22) + 1420070400000) / 1000,
            tz=UTC)
    ).total_seconds()


@router.head(
    '/{channel_id}/{message_id}',
    name='Check Message',
    description="""
        Check if a message was either deleted or created by /plu/ral""",
    responses={
        200: response(
            description='Message found',
            content=None),
        400: response(
            description='Message is in the future; status is unknown',
            content=None),
        404: response(
            description='Message was not found',
            content=None),
        410: response(
            description='Message is older than 7 days; status is unknown',
            content=None),
        422: response(
            description='Validation Error',
            content=None)})
@name('/messages/:id/:id')
@ratelimit(5, timedelta(seconds=5), auth=False)
@ratelimit(30, timedelta(seconds=10), ['channel_id'])
async def head__message(
    channel_id: int,
    message_id: int
) -> Response:
    if _snowflake_to_age(message_id) > 604_800:  # 7 days
        return Response(
            status_code=410,
            headers={'Cache-Control': 'public, max-age=604800'}
        )

    if _snowflake_to_age(message_id) < -30:
        return Response(status_code=400)

    pending = await redis.exists(f'pending_proxy:{channel_id}:{message_id}')

    if pending:
        return Response(
            status_code=200,
            headers={'Cache-Control': 'public, max-age=604800'}
        )

    message = await Message.find_one({
        'channel_id': channel_id,
        '$or': [
            {'original_id': message_id},
            {'proxy_id': message_id}
        ]
    })

    if message is None:
        return Response(
            status_code=404,
            headers={'Cache-Control': 'public, max-age=604800'}
        )

    return Response(
        status_code=200,
        headers={'Cache-Control': 'public, max-age=604800'}
    )


@router.get(
    '/{channel_id}/{message_id}',
    name='Get Message',
    description=dedent("""
    Get a message by its id

    Note: Because /plu/ral deletes and proxies messages simultaneously, this endpoint may block for up to 5 seconds waiting for the proxied message to be created, returning a 404 on timeout."""),
    responses={
        200: message_response,
        400: response(
            description='Message is in the future; status is unknown',
            examples=[Example(
                name='Message is in the future',
                value={'detail': 'Message is in the future; status is unknown'})]),
        404: response(
            description='Message not found',
            examples=[
                Example(
                    name='Message not found',
                    value={'detail': 'Message not found'}),
                Example(
                    name='Message not found (timeout)',
                    value={'detail': 'Message not found (timeout)'})]),
        410: response(
            description='Message is older than 7 days; status is unknown',
            examples=[Example(
                name='Message is older than 7 days',
                value={'detail': 'Message is older than 7 days; status is unknown'})])})
@name('/messages/:id/:id')
@ratelimit(20, timedelta(seconds=10), ['channel_id'])
async def get__message(
    channel_id: int,
    message_id: int,
    token: TokenData = Security(api_key_validator)  # noqa: ARG001, B008
) -> Response:
    if _snowflake_to_age(message_id) > 604_800:  # 7 days
        return Response(
            status_code=410,
            headers={'Cache-Control': 'public, max-age=604800'},
            media_type='application/json',
            content=dumps(
                {'detail': 'Message is older than 7 days; status is unknown'}
            )
        )

    if _snowflake_to_age(message_id) < -30:
        return Response(
            status_code=400,
            media_type='application/json',
            content=dumps(
                {'detail': 'Message is in the future; status is unknown'}
            )
        )

    pending = await redis.exists(f'pending_proxy:{channel_id}:{message_id}')

    message = await Message.find_one({
        'channel_id': channel_id,
        '$or': [
            {'original_id': message_id},
            {'proxy_id': message_id}
        ]
    })

    if message is None and not pending:
        return Response(
            status_code=404,
            headers={'Cache-Control': 'public, max-age=604800'},
            media_type='application/json',
            content=dumps({'detail': 'Message not found'})
        )

    limit = 50
    while message is None and limit > 0:
        await sleep(0.1)
        limit -= 1
        message = await Message.find_one({
            'channel_id': channel_id,
            '$or': [
                {'original_id': message_id},
                {'proxy_id': message_id}
            ]
        })

    if message is None:
        return Response(
            status_code=404,
            headers={'Cache-Control': 'public, max-age=604800'},
            media_type='application/json',
            content=dumps({'detail': 'Message not found (timeout)'})
        )

    return Response(
        status_code=200,
        media_type='application/json',
        headers={'Cache-Control': 'public, max-age=604800'},
        content=MessageModel.from_message(
            message
        ).model_dump_json()
    )


@router.get(
    '/{channel_id}/{message_id}/member',
    name='Get Message Member',
    description="""
    Get a message author by message id""",
    responses={
        200: author_response,
        400: response(
            description='Message is in the future; status is unknown',
            examples=[Example(
                name='Message is in the future',
                value={'detail': 'Message is in the future; status is unknown'})]),
        404: response(
            description='Message or Member not found',
            examples=[
                Example(
                    name='Message not found',
                    value={'detail': 'Message not found'}),
                Example(
                    name='Message not found (timeout)',
                    value={'detail': 'Message not found (timeout)'}),
                Example(
                    name='Member not found',
                    value={'detail': 'Member not found'})]),
        410: response(
            description='Message is older than 7 days; status is unknown',
            examples=[Example(
                name='Message is older than 7 days',
                value={'detail': 'Message is older than 7 days; status is unknown'})])})
@name('/messages/:id/:id/member')
@ratelimit(20, timedelta(seconds=10), ['channel_id'])
async def get__message_member(
    channel_id: int,
    message_id: int,
    token: TokenData = Security(api_key_validator)  # noqa: ARG001, B008
) -> Response:
    if _snowflake_to_age(message_id) > 604_800:  # 7 days
        return Response(
            status_code=410,
            headers={'Cache-Control': 'public, max-age=604800'},
            media_type='application/json',
            content=dumps(
                {'detail': 'Message is older than 7 days; status is unknown'}
            )
        )

    if _snowflake_to_age(message_id) < -30:
        return Response(
            status_code=400,
            media_type='application/json',
            content=dumps(
                {'detail': 'Message is in the future; status is unknown'}
            )
        )

    pending = await redis.exists(f'pending_proxy:{channel_id}:{message_id}')

    message = await Message.find_one({
        'channel_id': channel_id,
        '$or': [
            {'original_id': message_id},
            {'proxy_id': message_id}
        ]
    })

    if message is None and not pending:
        return Response(
            status_code=404,
            headers={'Cache-Control': 'public, max-age=604800'},
            media_type='application/json',
            content=dumps({'detail': 'Message not found'})
        )

    limit = 50
    while message is None and limit > 0:
        await sleep(0.1)
        limit -= 1
        message = await Message.find_one({
            'channel_id': channel_id,
            '$or': [
                {'original_id': message_id},
                {'proxy_id': message_id}
            ]
        })

    if message is None:
        return Response(
            status_code=404,
            headers={'Cache-Control': 'public, max-age=604800'},
            media_type='application/json',
            content=dumps({'detail': 'Message not found (timeout)'})
        )

    member = await ProxyMember.get(message.member_id)

    if member is None:
        return Response(
            status_code=404,
            headers={'Cache-Control': 'public, max-age=604800'},
            media_type='application/json',
            content=dumps({'detail': 'Member not found'})
        )

    usergroup = await (await member.get_group()).get_usergroup()

    return Response(
        status_code=200,
        media_type='application/json',
        content=AuthorModel.from_member(
            usergroup,
            member
        ).model_dump_json()
    )
