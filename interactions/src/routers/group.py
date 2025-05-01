from datetime import timedelta

from fastapi import APIRouter, Security, Depends, Response, Query
from beanie import PydanticObjectId
from orjson import dumps

from plural.db import Group, Usergroup

from src.core.auth import TokenData, api_key_validator, authorized_group, authorized_user
from src.core.ratelimit import ratelimit
from src.core.route import name

from src.models import GroupModel

from src.docs import (
    multi_group_response,
    group_response,
    response,
    Example
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


@router.get(
    '/{user_id}/groups',
    name='Get User Groups',
    description="""
    Get a user's groups by id or usergroup id

    Requires authorized user""",
    responses={
        200: multi_group_response,
        404: response(
            description='No Groups found',
            examples=[Example(
                name='No Groups found',
                value={'detail': 'No Groups found.'})])})
@name('/users/:id/groups')
@ratelimit(1, timedelta(seconds=5), ['user_id'])
async def get__user_groups(
    user_id: int | PydanticObjectId,  # noqa: ARG001
    token: TokenData = Security(api_key_validator),  # noqa: ARG001, B008
    usergroup: Usergroup = Depends(authorized_user),  # noqa: B008
    limit: int = Query(
        default=50, ge=1, le=100,
        description='Number of groups to return'),
    skip: int = Query(
        default=0, ge=0,
        description='Number of groups to skip')
) -> Response:
    groups = await Group.find({
        'account': usergroup.id
    }, skip=skip, limit=limit).to_list()

    if not groups:
        return Response(
            status_code=404,
            media_type='application/json',
            content=dumps({'detail': 'No Groups found.'})
        )

    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps([
            GroupModel.from_group(group).model_dump(mode='json')
            for group in groups
        ])
    )
