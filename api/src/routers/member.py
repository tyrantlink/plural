from datetime import timedelta
from typing import NamedTuple

from fastapi import APIRouter, Security, Depends, Response
from beanie import PydanticObjectId

from plural.errors import NotFound
from plural.db import ProxyMember
from plural.otel import cx

from src.core.auth import TokenData, api_key_validator, authorized_member
from src.core.ratelimit import ratelimit
from src.models import UserproxySync
from src.core.models import env
from src.core.route import name
from src.discord import User


router = APIRouter(prefix='/members', tags=['Members'])


class FakeInteraction(NamedTuple):
    author_id: int
    author_name: str


@router.post(
    '/{member_id}/userproxy/sync')
@name('/members/:oid/userproxy/sync')
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

    await _userproxy_sync(
        FakeInteraction(
            author_id=body.author_id,
            author_name=user.username),
        member,
        body.patch_filter,
        silent=True
    )

    return Response(status_code=(
        204
    ))
