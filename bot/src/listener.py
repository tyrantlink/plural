from asyncio import gather, sleep
from contextlib import suppress

from orjson import loads

from plural.db import redis, Message, ProxyMember
from plural.errors import Forbidden
from plural.otel import span

from .logic import process_proxy, get_webhook
from .http import Route, request
from .logclean import logclean
from .cache import Cache
from .models import env


async def on_event(redis_id: str, event_json: str, start_time: int) -> None:
    event = loads(event_json)

    match event['t']:
        case 'MESSAGE_CREATE':
            await gather(
                on_message_create(event['d'], start_time),
                logclean(event['d'], start_time))
        case 'MESSAGE_UPDATE':
            await on_message_update(event['d'], start_time)
        case 'MESSAGE_REACTION_ADD':
            await on_reaction_add(event['d'], start_time)
        case 'WEBHOOKS_UPDATE':
            await on_webhooks_update(event['d'], start_time)
        case _:
            raise ValueError(f'Unknown event type: {event['t']}')

    await redis.xack('discord_events', 'plural_consumers', redis_id)


def _preproxy_check(event: dict) -> bool:
    return (
        event.get('author') is None or
        event['author'].get('bot') or
        event.get('guild_id') is None or
        event.get('type') not in {0, 19}
    )


async def _send_error_message(
    channel_id: str,
    message_id: str
) -> None:
    with suppress(Forbidden):
        error_message = await request(
            Route(
                'POST',
                '/channels/{channel_id}/messages',
                token=env.bot_token,
                channel_id=channel_id),
            json={
                'content': (
                    'Failed to delete this message, missing permissions.\n\n'
                    '(This message will be deleted in 10 seconds)'),
                'message_reference': {'message_id': message_id}
            }
        )

        await sleep(10)

        await request(Route(
            'DELETE',
            '/channels/{channel_id}/messages/{message_id}',
            token=env.bot_token,
            channel_id=channel_id,
            message_id=error_message['id']
        ))


async def on_message_create(event: dict, start_time: int) -> None:
    if _preproxy_check(event):
        return

    await process_proxy(event, start_time)


async def on_message_update(event: dict, start_time: int) -> None:
    if _preproxy_check(event):
        return

    channel = await Cache.get(f'discord:channel:{event['channel_id']}')

    if (
        channel is None or
        channel.data.get('last_message_id') != event['id'] or
        await redis.get(f'pending_proxy:{event['channel_id']}:{event['id']}')
    ):
        return

    await process_proxy(event, start_time)


async def on_reaction_add(event: dict, start_time: int) -> None:
    if (
        event.get('user_id') == str(env.application_id) or
        event.get('guild_id') is None or
        event.get('member') is None or
        event['member'].get('user') is None or
        event['member']['user'].get('bot', False) or
        event.get('emoji', {}).get('name') != '❌'
    ):
        return

    db_message = await Message.find_one({
        'proxy_id': int(event['message_id'])
    })

    if db_message is None:
        return

    if int(event['user_id']) != db_message.author_id:
        return

    channel = await Cache.get(f'discord:channel:{event['channel_id']}')

    if channel is None:
        return

    with span('reaction delete', start_time=start_time):
        if event.get('message_author_id') is None:
            webhook = await get_webhook(
                event,
                False,
                (
                    str(db_message.webhook_id)
                    if db_message.webhook_id is not None
                    else None
                )
            )

            try:
                await request(
                    Route(
                        'DELETE',
                        '/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}',
                        token=env.bot_token,
                        webhook_id=webhook['id'],
                        webhook_token=webhook['token'],
                        message_id=event['message_id']),
                    params=(
                        {'thread_id': event['channel_id']}
                        if channel.data.get('type') in {11, 12}
                        else None))
            except Forbidden:
                await _send_error_message(event['channel_id'], event['id'])

            return

        member = await ProxyMember.find_one({
            'userproxy.bot_id': int(event['message_author_id'])
        })

        if member is None:
            return

        await request(Route(
            'DELETE',
            f'/channels/{event['channel_id']}/messages/{event['message_id']}',
            token=member.userproxy.token
        ))


async def on_webhooks_update(
    event: dict,
    start_time: int,
    internal: bool = False
) -> None:
    with span(
        'webhooks update',
        start_time=start_time,
        attributes={
            'channel_id': event['channel_id'],
            'guild_id': event['guild_id']
        }
    ):
        pipeline = redis.pipeline()

        await pipeline.delete(f'discord:webhooks:{event['channel_id']}')

        try:
            webhooks = await request(Route(
                'GET',
                '/channels/{channel_id}/webhooks',
                token=env.bot_token,
                channel_id=event['channel_id']))
        except Forbidden:
            if internal:
                raise
            return

        await pipeline.json().set(
            f'discord:webhooks:{event['channel_id']}',
            '$',
            webhooks
        )

        await pipeline.execute()
