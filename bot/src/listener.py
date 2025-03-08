from asyncio import gather

from orjson import loads

from plural.db import redis, Message, ProxyMember
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
            raise ValueError(f'Unknown event type: {event["t"]}')

    await redis.xack('discord_events', 'plural_consumers', redis_id)


def _preproxy_check(event: dict) -> bool:
    return (
        event.get('author') is None or
        event['author'].get('bot') or
        event.get('guild_id') is None or
        event.get('type') not in {0, 19}
    )


async def on_message_create(event: dict, start_time: int) -> None:
    if _preproxy_check(event):
        return

    await process_proxy(event, start_time, False)


async def on_message_update(event: dict, start_time: int) -> None:
    if _preproxy_check(event):
        return

    channel = await Cache.get(f'discord:channel:{event["channel_id"]}')

    if (
        channel is None or
        channel.data.get('last_message_id') != event['id'] or
        await redis.get(f'pending_proxy:{event["id"]}')
    ):
        return

    await process_proxy(event, start_time, True)


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

    channel = await Cache.get(f'discord:channel:{event["channel_id"]}')

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
                    else None
                )
            )
            return

        member = await ProxyMember.find_one({
            'userproxy.bot_id': int(event['message_author_id'])
        })

        if member is None:
            return

        await request(Route(
            'DELETE',
            f'/channels/{event["channel_id"]}/messages/{event["message_id"]}',
            token=member.userproxy.token
        ))


async def on_webhooks_update(event: dict, start_time: int) -> None:
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

        webhooks = await request(Route(
            'GET',
            '/channels/{channel_id}/webhooks',
            token=env.bot_token,
            channel_id=event['channel_id']
        ))

        await pipeline.json().set(
            f'discord:webhooks:{event['channel_id']}',
            '$',
            webhooks
        )

        await pipeline.execute()
