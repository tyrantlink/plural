from src.core.auth import discord_key_validator, gateway_key_validator
from fastapi import APIRouter, HTTPException, Depends
# from src.core.models.discord import Interaction, InteractionType
from fastapi.responses import Response, JSONResponse
from src.discord import GatewayEvent, GatewayEventName, MessageReactionAddEvent, MessageCreateEvent, MessageUpdateEvent
# from .commands import on_command, on_modal_submit
from asyncio import create_task
from src.listeners import on_reaction_add, on_message_create, on_message_update

router = APIRouter(prefix='/discord', tags=['UserProxy'])

ACCEPTED_EVENTS = {
    GatewayEventName.MESSAGE_CREATE,
    GatewayEventName.MESSAGE_UPDATE,
    GatewayEventName.MESSAGE_REACTION_ADD
}


@router.post(
    '/interaction',
    include_in_schema=False,
    dependencies=[Depends(discord_key_validator)])
async def post__interaction(
    interaction: dict
) -> Response:
    print(interaction)
    # match interaction.type:
    #     case InteractionType.PING:
    #         return JSONResponse({'type': 1})
    #     case InteractionType.APPLICATION_COMMAND:
    #         ...
    #         # await on_command(interaction)
    #     case InteractionType.MODAL_SUBMIT:
    #         ...
    #         # await on_modal_submit(interaction)
    #     case _:
    #         raise HTTPException(400, 'Unsupported interaction type')

    return Response(status_code=202)


@router.post(
    '/event',
    include_in_schema=False,
    dependencies=[Depends(gateway_key_validator)])
async def post__event(
    event: GatewayEvent
) -> Response:
    from json import dumps
    print(dumps(event._raw, indent=1))

    match event.name:
        case GatewayEventName.MESSAGE_CREATE:
            create_task(on_message_create(MessageCreateEvent(**event.data)))
        case GatewayEventName.MESSAGE_UPDATE:
            create_task(on_message_update(MessageUpdateEvent(**event.data)))
        case GatewayEventName.MESSAGE_REACTION_ADD:
            create_task(on_reaction_add(MessageReactionAddEvent(**event.data)))

    return Response(event.name, status_code=200)
