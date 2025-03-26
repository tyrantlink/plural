from datetime import timedelta

from fastapi import APIRouter, Security, Response

from plural.db.enums import ApplicationScope
from plural.errors import NotFound
from plural.db import Usergroup

from src.core.auth import TokenData, api_key_validator
from src.discord import User, Embed, ActionRow
from src.core.ratelimit import ratelimit
from src.core.models import env
from src.core.route import name


router = APIRouter(prefix='/users', tags=['Members'])


@router.post(
    '/{user_id}/authorize')
@name('/users/:id/authorize')
@ratelimit(1, timedelta(hours=1), ['user_id'])
async def post__users_authorize(
    user_id: int,
    token: TokenData = Security(api_key_validator)  # noqa: B008
) -> Response:
    from src.components.api import button_authorize, button_deny

    try:
        user = await User.fetch(
            user_id,
            env.bot_token)
    except NotFound:
        return Response(status_code=404)

    usergroup = await Usergroup.find_one({
        'users': user_id
    })

    if usergroup is None:
        return Response(status_code=404)

    await user.send_message(
        embeds=[
            Embed.success(
                title='Authorization Request',
                message=(
                    f'{token.application.name} is requesting '
                    'access to your /plu/ral data.')
            ).add_field(
                'Scopes',
                '\n'.join(
                    scope.pretty_name
                    for scope in
                    ApplicationScope
                    if (
                        scope & token.application.scope and
                        scope != ApplicationScope.LOGGING)
                ) or 'None')],
        components=[
            ActionRow(components=[
                button_authorize.with_overrides(
                    extra=[str(token.app_id), token.application.scope.value]),
                button_deny
            ])
        ]
    )

    return Response(status_code=204)
