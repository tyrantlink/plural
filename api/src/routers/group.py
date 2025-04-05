from datetime import timedelta

from fastapi import APIRouter, Security, Depends, Response
from beanie import PydanticObjectId
from orjson import dumps

from plural.db import Group

from src.core.auth import TokenData, api_key_validator, authorized_group
from src.core.ratelimit import ratelimit
from src.core.route import name

from src.models import GroupModel

from src.docs import (
    group_response,
    response
)


router = APIRouter(prefix='/groups', tags=['Groups'])


@router.get(
    '/{group_id}',
    name='Get Group',
    description="""
    Get a group by id

    Requires authorized user""",
    responses={
        200: group_response,
        403: response(
            description='Application not authorized to access this group',
            content=None),
        404: response(
            description='Group not found',
            content=None)})
@name('/members/:id')
@ratelimit(5, timedelta(seconds=30), ['group_id'])
async def get__member(
    group_id: PydanticObjectId,  # noqa: ARG001
    token: TokenData = Security(api_key_validator),  # noqa: ARG001, B008
    group: Group = Depends(authorized_group)  # noqa: B008
) -> Response:
    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps(GroupModel.from_group(
            group
        ).model_dump(mode='json'))
    )
