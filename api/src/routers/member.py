from datetime import timedelta
from typing import NamedTuple

from fastapi import APIRouter, Security, Depends, Response
from beanie import PydanticObjectId
from orjson import dumps

from plural.errors import NotFound, HTTPException
from plural.db import ProxyMember
from plural.otel import cx

from src.core.auth import TokenData, api_key_validator, authorized_member
from src.core.ratelimit import ratelimit
from src.models import UserproxySync
from src.core.models import env
from src.core.route import name
from src.discord import User

from src.models import MemberModel

from src.docs import (
    member_response,
    response,
    Example
)


router = APIRouter(prefix='/members', tags=['Members'])


class FakeInteraction(NamedTuple):
    author_id: int
    author_name: str


@router.get(
    '/{member_id}',
    name='Get Member',
    description="""
        Get a member by id

    Requires authorized user""",
    responses={
        200: member_response,
        403: response(
            description='Application not authorized to access this member',
            content=None),
        404: response(
            description='Member not found',
            content=None)})
@name('/members/:id')
@ratelimit(5, timedelta(seconds=30), ['member_id'])
async def get__member(
    member_id: PydanticObjectId,  # noqa: ARG001
    token: TokenData = Security(api_key_validator),  # noqa: B008
    member: ProxyMember = Depends(authorized_member)  # noqa: B008
) -> Response:
    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps(MemberModel.from_member(
            await (await member.get_group()).get_usergroup(),
            member,
            token
        ).model_dump(mode='json'))
    )


@router.post(
    '/{member_id}/userproxy/sync',
    name='Sync Userproxy',
    status_code=204,
    description="""
    Sync a member's userproxy

    Requires authorized user""",
    responses={
        204: response(
            description='Userproxy synced',
            content=None),
        400: response(
            description='Discord error',
            examples=[Example(
                name='Username rate limit',
                value={'detail': {
                    'discord_error': {
                        'message': 'Invalid Form Body', 'code': 50035,
                        'errors': {'username': {
                            '_errors': [{
                                'code': 'USERNAME_RATE_LIMIT',
                                'message': 'You are changing your username or Discord Tag too fast. Try again later.'
                            }]
                        }}
                    }
                }}
            )]),
        403: response(
            'Application not authorized to access this member',
            content=None),
        404: response(
            description='Member not found or user not found',
            content=None)})
@name('/members/:id/userproxy/sync')
@ratelimit(1, timedelta(seconds=30), ['member_id'])
async def post__member_userproxy_sync(
    member_id: PydanticObjectId,  # noqa: ARG001
    body: UserproxySync,
    token: TokenData = Security(api_key_validator),  # noqa: ARG001,B008
    member: ProxyMember = Depends(authorized_member)  # noqa: B008
) -> Response:
    from src.commands.userproxy import _userproxy_sync

    cx().set_attribute('patch_filter', list(body.patch_filter))

    try:
        user = await User.fetch(
            body.author_id,
            env.bot_token)
    except NotFound:
        return Response(status_code=404)

    try:
        await _userproxy_sync(
            FakeInteraction(
                author_id=body.author_id,
                author_name=user.username),
            member,
            body.patch_filter,
            silent=True)
    except HTTPException as e:
        return Response(
            status_code=400,
            media_type='application/json',
            content=dumps({
                'detail': {
                    'discord_error': e.detail or None
                }
            })
        )

    return Response(status_code=204)
