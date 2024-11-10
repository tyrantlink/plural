from src.core.auth import discord_key_validator, gateway_key_validator
from fastapi import APIRouter, HTTPException, Depends
# from src.core.models.discord import Interaction, InteractionType
from fastapi.responses import Response, JSONResponse
from src.discord import GatewayEvent, GatewayEventName, MessageReactionAddEvent, MessageCreateEvent, MessageUpdateEvent
# from .commands import on_command, on_modal_submit
from asyncio import create_task
from src.discord.types import ListenerType
from src.discord.listeners import emit

router = APIRouter(prefix='/discord', tags=['UserProxy'])

ACCEPTED_EVENTS = {
    GatewayEventName.MESSAGE_CREATE,
    GatewayEventName.MESSAGE_UPDATE,
    GatewayEventName.MESSAGE_REACTION_ADD,
    GatewayEventName.GUILD_UPDATE,
    GatewayEventName.CHANNEL_UPDATE
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
    if event.name not in ACCEPTED_EVENTS:
        return Response(event.name, status_code=200)

    match event.name:
        case GatewayEventName.MESSAGE_CREATE:
            listener = emit(
                ListenerType.MESSAGE_CREATE,
                await MessageCreateEvent.validate_and_populate(event.data))
        case GatewayEventName.MESSAGE_UPDATE:
            listener = emit(
                ListenerType.MESSAGE_UPDATE,
                MessageUpdateEvent(**event.data))
        case GatewayEventName.MESSAGE_REACTION_ADD:
            listener = emit(
                ListenerType.MESSAGE_REACTION_ADD,
                MessageReactionAddEvent(**event.data)
            )
        case GatewayEventName.GUILD_UPDATE:
            ...
        case GatewayEventName.CHANNEL_UPDATE:
            ...
        case _:
            print(event.data)
            return Response(event.name, status_code=200)
            raise HTTPException(500, 'event accepted but not handled')

    create_task(listener)

    return Response(event.name, status_code=200)
