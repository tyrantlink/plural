from time import time

from fastapi.responses import Response, JSONResponse
from fastapi import APIRouter, Depends

from src.core.auth import discord_key_validator
from src.discord import (
    EventWebhooksType,
    WebhookEventType,
    InteractionType,
    WebhookEvent,
    Interaction,
)

from plural.utils import create_strong_task
from plural.db import ProxyMember, redis


router = APIRouter(include_in_schema=False)
PONG = JSONResponse({'type': 1})


@router.post(
    '/interaction',
    dependencies=[Depends(discord_key_validator)])
@router.post(  # ? legacy route
    '/discord/interaction',
    dependencies=[Depends(discord_key_validator)])
@router.post(  # ? legacy route
    '/userproxy/interaction',
    dependencies=[Depends(discord_key_validator)])
async def post__interaction(
    interaction: Interaction
) -> Response:
    # ? immediately pong for pings
    if interaction.type == InteractionType.PING:
        return PONG

    pipeline = redis.pipeline()

    pipeline.lpush(
        'interaction_latency',
        round(time()*1000-((interaction.id >> 22) + 1420070400000)))
    pipeline.ltrim('interaction_latency', 0, 99)

    await pipeline.execute()

    create_strong_task(interaction.process())

    return Response(status_code=202)


@router.post(
    '/event',
    dependencies=[Depends(discord_key_validator)])
@router.post(  # ? legacy route
    '/discord/event',
    dependencies=[Depends(discord_key_validator)])
async def post__event(
    event: WebhookEvent
) -> Response:
    if (
        event.type == WebhookEventType.PING or
        event.event.type != EventWebhooksType.APPLICATION_AUTHORIZED or
        event.event.data.get('guild') is None
    ):
        return Response(status_code=204)

    member = await ProxyMember.find_one({
        'userproxy.bot_id': event.application_id
    })

    if member is None:
        return Response(status_code=204)

    member.userproxy.guilds.add(int(event.event.data['guild']['id']))

    await member.save()

    return Response(status_code=204)
