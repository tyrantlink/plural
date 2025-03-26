from collections.abc import Coroutine
from asyncio import Task, create_task
from time import time

from fastapi.responses import Response, JSONResponse
from fastapi import APIRouter, Depends

from src.core.auth import discord_key_validator
from src.core.models import env
from src.discord import (
    EventWebhooksType,
    WebhookEventType,
    InteractionType,
    WebhookEvent,
    Interaction,
)

from plural.db import ProxyMember, redis

from src.core.route import suppress, name

from .donation import make_donator


router = APIRouter(include_in_schema=False)
PONG = JSONResponse({'type': 1})
RUNNING: set[Task] = set()


def create_strong_task(coroutine: Coroutine) -> Task:
    task = create_task(coroutine)

    RUNNING.add(task)

    task.add_done_callback(RUNNING.discard)

    return task


@router.post(
    '/interaction',
    dependencies=[Depends(discord_key_validator)])
@router.post(  # ? legacy route
    '/discord/interaction',
    dependencies=[Depends(discord_key_validator)])
@router.post(  # ? legacy route
    '/userproxy/interaction',
    dependencies=[Depends(discord_key_validator)])
@suppress()
async def post__interaction(
    interaction: Interaction
) -> Response:
    # ? immediately pong for pings
    if interaction.type == InteractionType.PING:
        return PONG

    pipeline = redis.pipeline()

    latency = round(
        time()*1000-((interaction.id >> 22) + 1420070400000)
    )

    pipeline.lpush('interaction_latency', latency)
    pipeline.ltrim('interaction_latency', 0, 99)

    create_strong_task(interaction.process(latency))

    await pipeline.execute()

    return Response(status_code=202)


@router.post(
    '/event',
    dependencies=[Depends(discord_key_validator)])
@router.post(  # ? legacy route
    '/discord/event',
    dependencies=[Depends(discord_key_validator)])
@name('/event')
async def post__event(
    event: WebhookEvent
) -> Response:
    if event.type == WebhookEventType.PING:
        return Response(status_code=204)

    match event.event.type:
        case EventWebhooksType.APPLICATION_AUTHORIZED:
            if not event.event.data.guild:
                return Response(status_code=204)

            member = await ProxyMember.find_one({
                'userproxy.bot_id': event.application_id
            })

            if member is None:
                return Response(status_code=204)

            member.userproxy.guilds.add(int(event.event.data.guild.id))

            await member.save()
        case EventWebhooksType.ENTITLEMENT_CREATE:
            if (
                event.application_id != env.application_id or
                not event.event.data.user_id
            ):
                return Response(status_code=204)

            await make_donator(event.event.data.user_id)

    return Response(status_code=204)
