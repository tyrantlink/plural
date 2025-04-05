from datetime import timedelta

from fastapi import APIRouter, Security, Depends, Response
from beanie import PydanticObjectId
from orjson import dumps

from plural.errors import NotFound, Unauthorized, Forbidden
from plural.db.enums import ApplicationScope
from plural.db import Usergroup
from plural.otel import cx

from src.core.auth import TokenData, api_key_validator, authorized_user
from src.discord import User, Embed, ActionRow
from src.core.ratelimit import ratelimit
from src.core.models import env
from src.core.route import name

from src.models import UsergroupModel

from src.docs import (
    usergroup_response,
    response,
    Example
)


router = APIRouter(prefix='/users', tags=['Users'])


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
async def get__user(
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
