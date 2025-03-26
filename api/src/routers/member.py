from fastapi.responses import Response
from fastapi import APIRouter, Depends
from beanie import PydanticObjectId
from pydantic import BaseModel

from plural.db import ProxyMember

from src.core.auth import internal_key_validator


router = APIRouter(prefix='/members', tags=['Members'])


class UserproxySyncBody(BaseModel):
    author_id: int
    author_name: str
    patch_filter: set[str]


@router.post(
    '/{member_id}/userproxy/sync',
    dependencies=[Depends(internal_key_validator)])
async def post__member_userproxy_sync(
    member_id: PydanticObjectId,
    body: UserproxySyncBody
) -> Response:
    from src.commands.userproxy import _userproxy_sync
    member = await ProxyMember.get(member_id)

    if member is None:
        return Response(status_code=(
            404
        ))

    await _userproxy_sync(
        body,
        member,
        body.patch_filter,
        silent=True
    )

    return Response(status_code=(
        204
    ))
