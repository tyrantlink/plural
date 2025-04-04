from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Response, Security

from plural.db import redis, Message, ProxyMember

from src.core.auth import api_key_validator, TokenData
from src.models import MessageModel, AuthorModel
from src.core.ratelimit import ratelimit
from src.core.route import name

from src.docs import (
    message_response,
    response
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
@ratelimit(500, timedelta(seconds=1))
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
    description="""
    Get a message by its id""",
    responses={
        200: message_response,
        400: response(
            description='Message is in the future; status is unknown'),
        404: response(
            description='Message was not found'),
        410: response(
            description='Message is older than 7 days; status is unknown')})
@name('/messages/:id/:id')
@ratelimit(500, timedelta(seconds=1))
async def get__message(
    channel_id: int,
    message_id: int,
    token: TokenData = Security(api_key_validator)  # noqa: ARG001, B008
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
        200: {
            'description': 'Message Member found',
            'model': AuthorModel,
        },
        400: {
            'description': 'Message is in the future; status is unknown'},
        404: {
            'description': 'Message was not found or member was not found'
        },
        410: {
            'description': 'Message is older than 7 days; status is unknown'}})
@name('/messages/:id/:id/member')
@ratelimit(500, timedelta(seconds=1))
async def get__message_member(
    channel_id: int,
    message_id: int,
    token: TokenData = Security(api_key_validator)  # noqa: ARG001, B008
) -> Response:
    if _snowflake_to_age(message_id) > 604_800:  # 7 days
        return Response(
            status_code=410,
            headers={'Cache-Control': 'public, max-age=604800'}
        )

    if _snowflake_to_age(message_id) < -30:
        return Response(status_code=400)

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

    member = await ProxyMember.get(message.member_id)

    if member is None:
        return Response(
            status_code=404,
            headers={'Cache-Control': 'public, max-age=604800'}
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
