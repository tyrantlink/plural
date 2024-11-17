from src.discord import GatewayEvent, GatewayEventName, MessageReactionAddEvent, MessageCreateEvent, MessageUpdateEvent, Interaction, InteractionType
from src.core.auth import discord_key_validator, gateway_key_validator
from fastapi import APIRouter, HTTPException, Depends
from src.discord.http import _get_mime_type_for_image
from fastapi.responses import Response, JSONResponse
from src.discord.types import ListenerType
from src.db import HTTPCache, CFCDNProxy
from src.discord.listeners import emit
from asyncio import create_task

router = APIRouter(prefix='/discord', tags=['Discord'])
PONG = JSONResponse({'type': 1})

ACCEPTED_EVENTS = {
    GatewayEventName.MESSAGE_CREATE,
    GatewayEventName.MESSAGE_UPDATE,
    GatewayEventName.MESSAGE_REACTION_ADD,
    GatewayEventName.GUILD_UPDATE,
    GatewayEventName.CHANNEL_UPDATE,
    GatewayEventName.GUILD_ROLE_UPDATE,
    GatewayEventName.INTERACTION_CREATE,
}


@router.post(
    '/interaction',
    include_in_schema=False,
    dependencies=[Depends(discord_key_validator)])
async def post__interaction(
    interaction: Interaction
) -> Response:
    # ? immediately pong for pings
    if interaction.type == InteractionType.PING:
        return PONG

    await interaction.populate()

    create_task(emit(
        ListenerType.INTERACTION,
        interaction
    ))

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
        case GatewayEventName.INTERACTION_CREATE:
            task = emit(
                ListenerType.INTERACTION,
                Interaction.validate_and_populate(event.data)
            )
        case GatewayEventName.MESSAGE_CREATE:
            task = emit(
                ListenerType.MESSAGE_CREATE,
                await MessageCreateEvent.validate_and_populate(event.data))
        case GatewayEventName.MESSAGE_UPDATE:
            task = emit(
                ListenerType.MESSAGE_UPDATE,
                await MessageUpdateEvent.validate_and_populate(event.data))
        case GatewayEventName.MESSAGE_REACTION_ADD:
            task = emit(
                ListenerType.MESSAGE_REACTION_ADD,
                await MessageReactionAddEvent.validate_and_populate(event.data))
        case GatewayEventName.GUILD_UPDATE:
            task = HTTPCache.invalidate(f'/guilds/{event.data['id']}')
        case GatewayEventName.CHANNEL_UPDATE:
            task = HTTPCache.invalidate(f'/channels/{event.data['id']}')
        case GatewayEventName.GUILD_ROLE_UPDATE:
            task = HTTPCache.invalidate(f'/guilds/{event.data['guild_id']}')
        case _:
            raise HTTPException(500, 'event accepted but not handled')

    create_task(task)

    return Response(event.name, status_code=200)


@router.get(
    '/imageproxy/{proxy_id}',
    include_in_schema=False)
async def get__imageproxy(
    proxy_id: str
) -> Response:

    proxy = await CFCDNProxy.get(proxy_id)

    if proxy is None:
        raise HTTPException(404, 'image not found')

    return Response(
        content=proxy.data,
        media_type=_get_mime_type_for_image(proxy.data[:16])
    )
