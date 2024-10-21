from fastapi import APIRouter, HTTPException, Header, Depends, Request
from src.api.models.discord import Interaction, InteractionType
from .commands import on_command, on_modal_submit
from nacl.exceptions import BadSignatureError
from fastapi.responses import Response
from nacl.signing import VerifyKey
from src.db import UserProxy
from typing import Annotated
from json import loads

router = APIRouter(prefix='/userproxy', tags=['UserProxy'])


async def discord_key_validator(
    request: Request,
    x_signature_ed25519: Annotated[str, Header()],
    x_signature_timestamp: Annotated[str, Header()],
) -> bool:
    try:
        request_body = (await request.body()).decode()
        json_body = loads(request_body)
        application_id = int(json_body['application_id'])
    except Exception:
        raise HTTPException(400, 'Invalid request body')

    user_proxy = await UserProxy.find_one({'bot_id': application_id})

    if user_proxy is None:
        raise HTTPException(400, 'Invalid application id')

    verify_key = VerifyKey(bytes.fromhex(user_proxy.public_key))

    try:
        verify_key.verify(
            f'{x_signature_timestamp}{request_body}'.encode(),
            bytes.fromhex(x_signature_ed25519)
        )
    except BadSignatureError:
        raise HTTPException(401, 'Invalid request signature')

    user_id = int(json_body['authorizing_integration_owners']['1'])

    if user_proxy.user_id != user_id:
        member = await user_proxy.get_member()
        group = await member.get_group()

        if user_id not in group.accounts:
            raise HTTPException(401, 'Invalid user id')

    return True


@router.post(
    '/interaction',
    include_in_schema=False,
    dependencies=[Depends(discord_key_validator)])
async def post__interaction(
    interaction_raw: dict
) -> Response:
    interaction = Interaction(**interaction_raw)

    match interaction.type:
        case InteractionType.PING:
            await interaction.pong()
        case InteractionType.APPLICATION_COMMAND:
            await on_command(interaction)
        case InteractionType.MODAL_SUBMIT:
            await on_modal_submit(interaction)
        case _:
            raise HTTPException(400, 'Unsupported interaction type')

    return Response(status_code=202)
