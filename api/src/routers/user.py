from datetime import timedelta

from fastapi import APIRouter, Security, Depends, Response, Query
from beanie import PydanticObjectId
from orjson import dumps

from plural.db import Usergroup, AutoProxy, ProxyMember, Group
from plural.errors import NotFound, Unauthorized, Forbidden
from plural.db.enums import ApplicationScope
from plural.otel import cx

from src.core.auth import TokenData, api_key_validator, authorized_user
from src.discord import User, Embed, ActionRow
from src.core.ratelimit import ratelimit
from src.core.models import env
from src.core.route import name

from src.models import UsergroupModel, AutoProxyModel, MemberModel

from src.docs import (
    multi_member_response,
    autoproxy_response,
    usergroup_response,
    member_response,
    response,
    Example
)


router = APIRouter(prefix='/users', tags=['Users'])


@router.post(
    '/{user_id}/authorize',
    name='Authorize User',
    status_code=202,
    description="""
    Send an authorization request to a user, or automatically authorize with an OAuth token.""",
    responses={
        202: response(
            description='Authorization request sent',
            examples=[Example(
                name='Request sent',
                value={'detail': 'Authorization request sent.'})]),
        204: response(
            description='User automatically authorized',
            content=None),
        401: response(
            description='Invalid Discord OAuth token',
            examples=[Example(
                name='Invalid Discord OAuth token',
                value={'detail': 'Invalid Discord OAuth token.'})]),
        403: response(
            description='Invalid Discord OAuth token or User has DMs disabled',
            examples=[
                Example(
                    name='Invalid Discord OAuth token',
                    value={'detail': 'Invalid Discord OAuth token.'}),
                Example(
                    name='User has DMs disabled',
                    value={'detail': 'User has DMs disabled. Unable to request authorization.'})]),
        404: response(
            description='User not found or User has not registered',
            examples=[
                Example(
                    name='User not found',
                    value={'detail': 'User not found. (Discord)'}),
                Example(
                    name='User has not registered',
                    value={'detail': 'User has not registered with /plu/ral.'})])})
@name('/users/:id/authorize')
@ratelimit(1, timedelta(hours=1), ['user_id'])
async def post__users_authorize(
    user_id: int,
    token: TokenData = Security(api_key_validator),  # noqa: B008
    oauth: str | None = None,
) -> Response:
    from src.components.api import button_authorize, button_deny

    if oauth:
        try:
            user = await User.fetch_from_oauth(oauth)
        except Unauthorized:
            return Response(
                status_code=401,
                media_type='application/json',
                content=dumps({'detail': 'Invalid Discord OAuth token.'}))
        except Forbidden:
            return Response(
                status_code=403,
                media_type='application/json',
                content=dumps({'detail': 'Invalid Discord OAuth token.'}))
        except NotFound:
            return Response(
                status_code=404,
                media_type='application/json',
                content=dumps({'detail': 'Invalid Discord OAuth token.'}))
        except BaseException as e:
            cx().record_exception(e)
            raise

        embeds, components = [Embed.success(
            title='Automatic Authorization Complete',
            message=(
                f'{token.application.name} has been automatically '
                'authorized to access your /plu/ral data.\n\n'
                'If you did not authorize this, your Discord '
                'account may have been compromised.')
        )], []
    else:
        try:
            user = await User.fetch(
                user_id,
                env.bot_token)
        except NotFound:
            return Response(
                status_code=404,
                media_type='application/json',
                content=dumps({'detail': 'User not found. (Discord)'})
            )

        embeds, components = [Embed.success(
            title='Authorization Request',
            message=(
                f'{token.application.name} is requesting '
                'access to your /plu/ral data.')
        )], [ActionRow(components=[
            button_authorize.with_overrides(
                extra=[str(token.app_id), token.application.scope.value]),
            button_deny
        ])]

    embeds[0].add_field(
        'Scopes',
        '\n'.join(
            scope.pretty_name
            for scope in
            ApplicationScope
            if scope & token.application.scope
        ) or 'None'
    )

    usergroup = await Usergroup.find_one({
        'users': user.id
    })

    if usergroup is None:
        return Response(
            status_code=404,
            media_type='application/json',
            content=dumps({'detail': 'User has not registered with /plu/ral.'}))

    if oauth:
        usergroup.data.applications[str(
            token.app_id)] = token.application.scope
        await usergroup.save()
        return Response(status_code=204)

    try:
        await user.send_message(
            embeds=embeds,
            components=components)
        return Response(
            status_code=202,
            media_type='application/json',
            content=dumps({
                'detail': 'Authorization request sent.'}))
    except Forbidden:
        return Response(
            status_code=403,
            media_type='application/json',
            content=dumps({
                'detail': 'User has DMs disabled. Unable to request authorization.'
            })
        )


@router.get(
    '/{user_id}',
    name='Get User',
    description="""
    Get a user by id or usergroup id

    Requires authorized user""",
    responses={
        200: usergroup_response})
@name('/users/:id')
@ratelimit(10, timedelta(seconds=10), ['user_id'])
async def get__users(
    user_id: int | PydanticObjectId,  # noqa: ARG001
    token: TokenData = Security(api_key_validator),  # noqa: B008
    usergroup: Usergroup = Depends(authorized_user)  # noqa: B008
) -> Response:
    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps(UsergroupModel.from_usergroup(
            usergroup,
            token
        ).model_dump(mode='json'))
    )


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
async def get__users_autoproxy(
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
async def get__users_autoproxy_member(
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


@router.get(
    '/{user_id}/members',
    name='Get User Members',
    description="""
    Get a user's members by id or usergroup id

    Requires authorized user""",
    responses={
        200: multi_member_response,
        404: response(
            description='No Members found',
            examples=[Example(
                name='No Members found',
                value={'detail': 'No Members found.'})])})
@name('/users/:id/members')
@ratelimit(1, timedelta(seconds=5), ['user_id'])
async def get__users_members(
    user_id: int | PydanticObjectId,  # noqa: ARG001
    token: TokenData = Security(api_key_validator),  # noqa: B008
    usergroup: Usergroup = Depends(authorized_user),  # noqa: B008
    limit: int = Query(
        default=50, ge=1, le=100,
        description='Number of members to return'),
    skip: int = Query(
        default=0, ge=0,
        description='Number of members to skip'),
    user: int | None = Query(
        default=None,
        description='Specify Discord user id, to include shared groups')
) -> Response:
    members = await Group.aggregate([
        {'$match':
            {'$or': [
                {'account': usergroup.id},
                {f'users.{user}': {'$exists': True}}]}
            if user else
            {'account': usergroup.id}},
        {'$unwind': '$members'},
        {'$lookup': {
            'from': 'members',
            'localField': 'members',
            'foreignField': '_id',
            'as': 'member_details'}},
        {'$unwind': '$member_details'},
        {'$replaceRoot': {'newRoot': '$member_details'}},
        {'$sort': {'_id': 1}},
        {'$skip': skip},
        {'$limit': limit}
    ], projection_model=ProxyMember).to_list()

    if not members:
        return Response(
            status_code=404,
            media_type='application/json',
            content=dumps({'detail': 'No Members found.'})
        )

    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps([
            MemberModel.from_member(
                usergroup,
                member,
                token
            ).model_dump(mode='json')
            for member in members
        ])
    )
