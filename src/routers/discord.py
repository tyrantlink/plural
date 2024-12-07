from src.discord import GatewayEvent, GatewayEventName, MessageReactionAddEvent, MessageCreateEvent, MessageUpdateEvent, Interaction, InteractionType, WebhookEvent, WebhookEventType
from src.db import CFCDNProxy, GatewayEvent as DBGatewayEvent
from fastapi import APIRouter, HTTPException, Depends
from src.discord.http import _get_mime_type_for_image
from fastapi.responses import Response, JSONResponse
from src.core.auth import discord_key_validator
from pymongo.errors import DuplicateKeyError
from src.discord.types import ListenerType
from src.models import project, MISSING
from src.discord.listeners import emit
from src.logic import discord_cache
from asyncio import create_task
from hashlib import sha256
import logfire

router = APIRouter(prefix='/discord', tags=['Discord'])
PONG = JSONResponse({'type': 1})

ACCEPTED_EVENTS = {
    GatewayEventName.MESSAGE_CREATE,
    GatewayEventName.MESSAGE_UPDATE,
    GatewayEventName.INTERACTION_CREATE,
    GatewayEventName.MESSAGE_REACTION_ADD,
}


async def _handle_gateway_event(event: GatewayEvent) -> Response:
    if not project.dev_environment:
        request_hash = sha256(str(event.data).encode()).hexdigest()

        if await DBGatewayEvent.get(request_hash) is not None:
            return Response('DUPLICATE_EVENT', status_code=200)

        try:
            await DBGatewayEvent(
                id=request_hash,
                instance=str(id(MISSING))
            ).insert()
        except DuplicateKeyError:
            # ? event was inserted by another node between the check and insert attempt
            return Response('DUPLICATE_EVENT', status_code=200)

    try:  # ? temp try/except while work in progress
        await discord_cache(event)
    except Exception as e:
        logfire.error(
            'caching error on {event_name} event',
            event_name=event.name,
            _exc_info=e.with_traceback(e.__traceback__))

    if event.name not in ACCEPTED_EVENTS:
        return Response(event.name, status_code=200)

    match event.name:
        case GatewayEventName.INTERACTION_CREATE:
            task = emit(
                ListenerType.INTERACTION,
                await Interaction.validate_and_populate(event.data))
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
        case _:
            raise HTTPException(500, 'event accepted but not handled')

    create_task(task)

    return Response(event.name, status_code=200)


async def _handle_webhook_event(event: WebhookEvent) -> Response:
    # ? immediately pong for pings
    if event.type == WebhookEventType.PING:
        return Response(status_code=204)

    if not event.event:
        return Response(status_code=200)

    create_task(emit(
        ListenerType.WEBHOOK_EVENT,
        event
    ))

    return Response(status_code=200)


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
    dependencies=[Depends(discord_key_validator)])
async def post__event(
    event: GatewayEvent | WebhookEvent
) -> Response:
    if isinstance(event, GatewayEvent):
        return await _handle_gateway_event(event)

    return await _handle_webhook_event(event)


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
