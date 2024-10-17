from fastapi import APIRouter, HTTPException, Header, Depends, Request
from src.api.models.discord import Interaction, InteractionType
from nacl.exceptions import BadSignatureError
from fastapi.responses import Response
from nacl.signing import VerifyKey
from .commands import on_command
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
        application_id = int(loads(request_body)['application_id'])
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

    return True


@router.post(
    '/interaction',
    include_in_schema=False,
    dependencies=[Depends(discord_key_validator)])
async def post__interaction(
    interaction_raw: dict
) -> Response:
    print(interaction_raw)
    interaction = Interaction(**interaction_raw)
    if interaction.type == InteractionType.PING:
        return interaction.response.pong()

    if interaction.data is None:
        raise HTTPException(400, 'Invalid interaction data')

    if interaction.type == InteractionType.APPLICATION_COMMAND:
        return await on_command(interaction)

    #! handle modal submit here too

    raise HTTPException(400, 'Unsupported interaction type')
