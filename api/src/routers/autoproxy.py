from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Security, Depends, Response, Body
from beanie import PydanticObjectId
from orjson import dumps

from plural.db import Usergroup, AutoProxy, ProxyMember, redis

from src.core.auth import TokenData, api_key_validator, authorized_user
from src.core.ratelimit import ratelimit
from src.core.route import name

from src.models import (
    AutoProxyPutModel,
    AutoProxyModel,
    MemberModel,
)

from src.docs import (
    autoproxy_put_request,
    autoproxy_response,
    member_response,
    response,
    Example
)


router = APIRouter(prefix='/users', tags=['Autoproxy'])


@router.get(
    '/{user_id}/autoproxy',
    name='Get User Autoproxy',
    description="""
    Get a user's autoproxy by id or usergroup id

    Requires authorized user""",
    responses={
        200: autoproxy_response,
        404: response(
            description='Autoproxy not found',
            examples=[Example(
                name='Autoproxy not found',
                value={'detail': 'Autoproxy not found.'})])})
@name('/users/:id/autoproxy')
@ratelimit(10, timedelta(seconds=10), ['user_id'])
async def get__user_autoproxy(
    user_id: int | PydanticObjectId,  # noqa: ARG001
    guild_id: int | None = None,
    token: TokenData = Security(api_key_validator),  # noqa: ARG001, B008
    usergroup: Usergroup = Depends(authorized_user)  # noqa: B008
) -> Response:
    autoproxy = await AutoProxy.find_one({
        'user': usergroup.id,
        'guild': guild_id,
    })

    if autoproxy is None:
        return Response(
            status_code=404,
            media_type='application/json',
            content=dumps({'detail': 'Autoproxy not found.'})
        )

    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps(AutoProxyModel.model_validate(
            autoproxy,
            from_attributes=True
        ).model_dump(mode='json'))
    )


@router.get(
    '/{user_id}/autoproxy/member',
    name='Get User Autoproxy Member',
    description="""
    Get a user's autoproxy member by id or usergroup id

    Requires authorized user""",
    responses={
        200: member_response,
        400: response(
            description='Autoproxy member is not set;',
            examples=[Example(
                name='Autoproxy member is not set',
                value={'detail': 'Autoproxy member is not set.'})]),
        404: response(
            description='Autoproxy not found or member not found',
            examples=[
                Example(
                    name='Autoproxy not found',
                    value={'detail': 'Autoproxy not found.'}),
                Example(
                    name='Member not found',
                    value={'detail': 'Member not found.'})])})
@name('/users/:id/autoproxy/member')
@ratelimit(10, timedelta(seconds=10), ['user_id'])
async def get__user_autoproxy_member(
    user_id: int | PydanticObjectId,  # noqa: ARG001
    guild_id: int | None = None,
    token: TokenData = Security(api_key_validator),  # noqa: B008
    usergroup: Usergroup = Depends(authorized_user)  # noqa: B008
) -> Response:
    autoproxy = await AutoProxy.find_one({
        'user': usergroup.id,
        'guild': guild_id,
    })

    if autoproxy is None:
        return Response(
            status_code=404,
            media_type='application/json',
            content=dumps({'detail': 'Autoproxy not found.'})
        )

    if autoproxy.member is None:
        return Response(
            status_code=400,
            media_type='application/json',
            content=dumps({'detail': 'Autoproxy member is not set.'})
        )

    member = await ProxyMember.get(autoproxy.member)

    if member is None:
        return Response(
            status_code=404,
            media_type='application/json',
            content=dumps({'detail': 'Member not found.'})
        )

    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps(MemberModel.from_member(
            usergroup,
            member,
            token
        ).model_dump(mode='json'))
    )


@router.put(
    '/{user_id}/autoproxy',
    name='Set User Autoproxy',
    description="""
    Set a user's autoproxy by id or usergroup id

    Requires authorized user""",
    responses={
        200: autoproxy_response | {'description': 'Autoproxy Updated'},
        201: autoproxy_response | {'description': 'Autoproxy Created'},
        400: response(
            description='Invalid guild id',
            examples=[Example(
                name='Invalid guild id',
                value={'detail': 'Invalid guild id. Guild 844127424526680084 not found in /plu/ral database.'})])})
@name('/users/:id/autoproxy')
@ratelimit(2, timedelta(seconds=10), ['user_id'])
async def set__user_autoproxy(
    user_id: int | PydanticObjectId,  # noqa: ARG001
    autoproxy: Annotated[AutoProxyPutModel, Body(
        openapi_examples=autoproxy_put_request)],
    token: TokenData = Security(api_key_validator),  # noqa: ARG001, B008
    usergroup: Usergroup = Depends(authorized_user)  # noqa: B008
) -> Response:
    if (
        autoproxy.guild is not None and
        not await redis.exists(f'discord:guild:{autoproxy.guild}')
    ):
        return Response(
            status_code=400,
            media_type='application/json',
            content=dumps(
                {'detail': f'Invalid guild id. Guild {autoproxy.guild} not found in /plu/ral database.'}
            )
        )

    existing_autoproxy = await AutoProxy.find_one({
        'user': usergroup.id,
        'guild': autoproxy.guild,
    })

    status_code = 200 if existing_autoproxy else 201

    new_autoproxy = autoproxy.to_autoproxy(
        usergroup.id
    )

    final_autoproxy = await (
        existing_autoproxy.model_copy(
            update=new_autoproxy.model_dump(exclude={'id'}))
        if existing_autoproxy else
        new_autoproxy
    ).save()

    return Response(
        status_code=status_code,
        media_type='application/json',
        content=dumps(AutoProxyModel.model_validate(
            final_autoproxy,
            from_attributes=True
        ).model_dump(mode='json'))
    )
