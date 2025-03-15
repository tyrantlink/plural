from hmac import new as hmac, compare_digest
from contextlib import suppress
from typing import Annotated
from hashlib import md5

from fastapi import APIRouter, Depends, Request, Response, Header, HTTPException

from plural.errors import HTTPException as PluralHTTPException
from plural.db.enums import SupporterTier
from plural.db import Usergroup
from plural.otel import cx

from src.core.http import request, Route
from src.core.models import env

from .otel import trace


router = APIRouter(include_in_schema=False)


async def make_donator(discord_id: int) -> None:
    usergroup = await Usergroup.get_by_user(discord_id)

    usergroup.data.supporter_tier = SupporterTier.SUPPORTER

    await usergroup.save()

    # ? hard-coded because i don't have the attention span
    with suppress(PluralHTTPException):
        await request(Route(
            'POST',
            f'/guilds/844127424526680084/members/{discord_id}/roles/1305047206994382939',
            env.bot_token
        ))


async def patreon_validator(
    request: Request,
    x_patreon_signature: Annotated[str, Header()]
) -> None:
    try:
        request_body = await request.body()
    except Exception as e:
        raise HTTPException(400, 'Invalid request body') from e

    signature = hmac(
        env.patreon_secret.encode(),
        request_body,
        md5
    ).hexdigest()

    if not compare_digest(signature, x_patreon_signature):
        raise HTTPException(401, 'Invalid signature')


@router.post(
    '/donation/patreon',
    dependencies=[Depends(patreon_validator)])
@trace('/donation/patreon')
async def post__donation_patreon(
    request: Request,
    data: dict
) -> Response:
    cx().set_attribute(
        'patreon.event',
        request.headers.get('x-patreon-event')
    )

    for model in data.get('included', []):
        if model['type'] == 'user':
            user = model
            break
    else:
        raise HTTPException(400, 'User not provided')

    if not isinstance(user, dict):
        raise HTTPException(400, 'Invalid user object')

    discord_id = user.get(
        'attributes', {}
    ).get(
        'social_connections', {}
    ).get(
        'discord', {}
    ).get('user_id')

    if not isinstance(discord_id, str):
        raise HTTPException(400, 'Discord ID not provided')

    if not discord_id.isdigit():
        raise HTTPException(400, 'Invalid Discord ID')

    try:
        discord_id = int(discord_id)
    except ValueError as e:
        raise HTTPException(
            400, 'Invalid Discord ID'
        ) from e

    await make_donator(discord_id)

    return Response(status_code=204)
