from datetime import datetime, timedelta, UTC

from fastapi import APIRouter, Response, Security
from orjson import dumps

from plural.db import redis, Message, ProxyMember
from plural.db.enums import ApplicationScope

from src.core.auth import api_key_validator, TokenData
from src.models import MessageModel, AuthorModel
from src.core.ratelimit import ratelimit
from src.core.route import name


router = APIRouter(prefix='/messages', tags=['Messages'])


def _snowflake_to_age(snowflake: int) -> float:
    return (
        datetime.now(UTC) - datetime.fromtimestamp(
            ((snowflake >> 22) + 1420070400000) / 1000,
            tz=UTC)
    ).total_seconds()


@router.head(
    '/{channel_id}/{message_id}',
    description="""
        Check if a message was either deleted or created by /plu/ral""",
    responses={
        200: {
            'content': None,
            'description': 'Message found'},
        404: {
            'content': None,
            'description': 'Message was not found'},
        410: {
            'content': None,
            'description': 'Message is older than 7 days; status is unknown'},
        400: {
            'content': None,
            'description': 'Message is in the future; status is unknown'},
        422: {
            'content': None,
            'description': 'Validation Error'}})
@name('/messages/:id/:id')
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
    description="""
    Get a message by its id

    Requires logging scope""",
    responses={
        200: {
            'description': 'Message found',
            'model': MessageModel,
            'content': {
                'application/json': {
                    'examples': {
                        'Webhook proxy': {'value': {
                            'original_id': '1353206395104923681',
                            'proxy_id': '1353206397420179466',
                            'author_id': '250797109022818305',
                            'channel_id': '1307354421394669608',
                            'reason': 'Matched proxy tag ​`text`​`--steve`',
                            'webhook_id': '1347606225851912263'}},
                        'Userproxy bot proxy': {'value': {
                            'original_id': '1353202123797430272',
                            'proxy_id': '1353202124502073398',
                            'author_id': '250797109022818305',
                            'channel_id': '1292096869974937736',
                            'reason': 'Matched proxy tag ​`text`​`--steve`',
                            'webhook_id': None}},
                        'Userproxy command': {'value': {
                            'original_id': None,
                            'proxy_id': '1353212365616709693',
                            'author_id': '250797109022818305',
                            'channel_id': '1307354421394669608',
                            'reason': 'Userproxy /proxy command',
                            'webhook_id': None}},
                        'Webhook proxy (api)': {'value': {
                            'original_id': None,
                            'proxy_id': '1353206397420179466',
                            'author_id': '250797109022818305',
                            'channel_id': '1307354421394669608',
                            'reason': 'Matched proxy tag ​`text`​`--steve`',
                            'webhook_id': '1347606225851912263'}},
                        'Userproxy bot proxy (api)': {'value': {
                            'original_id': None,
                            'proxy_id': '1353202124502073398',
                            'author_id': '250797109022818305',
                            'channel_id': '1292096869974937736',
                            'reason': 'Matched proxy tag ​`text`​`--steve`',
                            'webhook_id': None
                        }},
                    }
                }
            }
        },
        400: {
            'description': 'Message is in the future; status is unknown'},
        403: {
            'description': 'Missing logging scope'
        },
        404: {
            'description': 'Message was not found'
        },
        410: {
            'description': 'Message is older than 7 days; status is unknown'}})
@name('/messages/:id/:id')
@ratelimit(500, timedelta(seconds=1))
async def get__message(
    channel_id: int,
    message_id: int,
    token: TokenData = Security(api_key_validator)  # noqa: B008
) -> Response:
    # ! figure out how to move this into the validator
    if not ApplicationScope.LOGGING & token.application.scope:
        return Response(
            status_code=403,
            media_type='application/json',
            content=dumps({'detail': {
                'loc': ['header', 'Authorization'],
                'msg': 'Missing required scope: logging',
                'type': 'permission_error'
            }})
        )

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
    description="""
    Get a message author by message id

    Requires logging scope""",
    responses={
        200: {
            'description': 'Message Member found',
            'model': AuthorModel,
        },
        400: {
            'description': 'Message is in the future; status is unknown'},
        403: {
            'description': 'Missing logging scope'
        },
        404: {
            'description': 'Message was not found or member was not found'
        },
        410: {
            'description': 'Message is older than 7 days; status is unknown'}
    })
@name('/messages/:id/:id/member')
@ratelimit(500, timedelta(seconds=1))
async def get__message_member(
    channel_id: int,
    message_id: int,
    token: TokenData = Security(api_key_validator)  # noqa: B008
) -> Response:
    if not ApplicationScope.LOGGING & token.application.scope:
        return Response(
            status_code=403,
            media_type='application/json',
            content=dumps({'detail': {
                'loc': ['header', 'Authorization'],
                'msg': 'Missing required scope: logging',
                'type': 'permission_error'
            }})
        )

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
        headers={'Cache-Control': 'public, max-age=604800'},
        content=AuthorModel.from_member(
            usergroup,
            member
        ).model_dump_json()
    )
