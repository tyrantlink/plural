from src.discord import GatewayEvent, GatewayEventName
from src.db import DiscordObject
from beanie import BulkWriter
from typing import Coroutine
from asyncio import gather
from copy import deepcopy

# ? this entire file is mildly gross, please do not look at it


async def _sync_member(event: GatewayEvent) -> Coroutine | None:
    if event.data.get('webhook_id', None) is not None:
        return None

    member_data = event.data['member']
    member_data.pop('user', None)
    user_id = event.data.get(
        'user_id', None
    ) or (
        event.data['author']['id']
    )

    member = await DiscordObject.get(
        user_id
    ) or DiscordObject(
        id=user_id,
        guild_id=event.data['guild_id'],
        data={}
    )

    return member.merge(member_data).save()


async def _sync_user(event: GatewayEvent, from_member: bool = True) -> Coroutine | None:
    user_data = (
        event.data['member']['user']
        if from_member
        else event.data['author']
    )

    user = await DiscordObject.get(
        user_data['id']
    ) or DiscordObject(
        id=user_data['id'],
        data={}
    )

    return user.merge(user_data).save()


def _content_strip(data: dict) -> dict:
    content_strip = {
        'content': '',
        'attachments': []
    }

    if data.get('referenced_message', None) is not None:
        content_strip['referenced_message'] = {'content': ''}

    return content_strip


async def _message_create(event: GatewayEvent) -> Coroutine:
    return DiscordObject(
        id=event.data['id'],
        data=event.data
    ).merge(
        _content_strip(event.data)
    ).save()


async def _message_update(event: GatewayEvent) -> Coroutine:
    original = await DiscordObject.get(
        event.data['id']
    ) or DiscordObject(
        id=event.data['id'],
        data={})

    return original.merge(
        event.data
    ).merge(
        _content_strip(event.data)
    ).save()


async def _message_delete(event: GatewayEvent) -> Coroutine | None:
    original = await DiscordObject.get(event.data['id'])

    if original is None:
        return None

    original.data = event.data
    original.deleted = True
    return original.save()


async def _message_reaction_add(event: GatewayEvent) -> Coroutine | None:
    message = await DiscordObject.get(event.data['message_id'])
    if message is None:
        return None

    message.data['reactions'] = message.data.get('reactions', [])

    existing_reaction = next(
        (
            reaction
            for reaction in message.data['reactions']
            if reaction['emoji'] == event.data['emoji']
        ),
        None
    )

    if existing_reaction is not None:
        index = message.data['reactions'].index(existing_reaction)

        existing_reaction['count_details'][
            'burst' if event.data['burst'] else 'normal'] += 1

        existing_reaction['count'] = sum(
            existing_reaction['count_details'].values())

        existing_reaction['burst_count'] = existing_reaction['count_details']['burst']

        message.data['reactions'][index] = existing_reaction
        return message.save()

    message.data['reactions'].append({
        'emoji': event.data['emoji'],
        'count': 1,
        'count_details': {
            'burst': int(event.data['burst']),
            'normal': int(not event.data['burst'])
        },
        'burst_colors': event.data.get('burst_colors', []),
        'burst_count': int(event.data['burst']),
        # ? /plu/ral never reads these, and they would be effort to implement
        # ? so they are hardcoded to False
        'me': False,
        'me_burst': False,
        'burst_me': False
    })

    return message.save()


async def _message_reaction_remove(event: GatewayEvent) -> Coroutine | None:
    message = await DiscordObject.get(event.data['message_id'])
    if message is None:
        return None

    message.data['reactions'] = message.data.get('reactions', [])

    existing_reaction = next(
        (
            reaction
            for reaction in message.data['reactions']
            if reaction['emoji'] == event.data['emoji']
        ),
        None
    )

    if existing_reaction is None:
        return None

    if existing_reaction['count'] == 1:
        message.data['reactions'].remove(existing_reaction)
        return message.save()

    existing_reaction['count_details'][
        'burst' if event.data['burst'] else 'normal'] -= 1
    existing_reaction['count'] = sum(
        existing_reaction['count_details'].values())
    existing_reaction['burst_count'] = existing_reaction['count_details']['burst']

    return message.save()


async def _channel_create(event: GatewayEvent) -> Coroutine:
    return DiscordObject(
        id=event.data['id'],
        data=event.data
    ).save()


async def _channel_update(event: GatewayEvent) -> Coroutine:
    channel = await DiscordObject.get(
        event.data['id']
    ) or DiscordObject(
        id=event.data['id'],
        data={}
    )

    return channel.merge(event.data).save()


async def _channel_delete(event: GatewayEvent) -> Coroutine | None:
    channel = await DiscordObject.get(event.data['id'])

    if channel is None:
        return None

    channel.data = event.data
    channel.deleted = True
    return channel.save()


async def _guild_role_create(event: GatewayEvent) -> Coroutine:
    return DiscordObject(
        id=event.data['role']['id'],
        guild_id=event.data['guild_id'],
        data=event.data['role']
    ).save()


async def _guild_create(event: GatewayEvent) -> Coroutine:
    guild_data = event.data

    members = guild_data.pop('members', [])

    roles = guild_data.pop('roles', [])

    channels = guild_data.pop('channels', [])

    objects = [
        DiscordObject(
            id=guild_data['id'],
            data=guild_data
        ),
        *[
            DiscordObject(
                id=member['user']['id'],
                data=member['user']
            )
            for member in members
        ],
        *[
            DiscordObject(
                id=user['id'],
                guild_id=guild_data['id'],
                data=member
            )
            for member in members
            # ? just popping user object
            if (user := member.pop('user', True))
        ],
        *[
            DiscordObject(
                id=role['id'],
                guild_id=guild_data['id'],
                data=role
            )
            for role in roles
        ],
        *[
            DiscordObject(
                id=channel['id'],
                guild_id=guild_data['id'],
                data=channel
            )
            for channel in channels
        ]
    ]

    async with BulkWriter() as writer:
        for obj in objects:
            await obj.find_one(
                {'_id': obj.id},
                upsert=True
            ).replace_one(obj, bulk_writer=writer)

        return writer.commit()


async def _guild_update(event: GatewayEvent) -> Coroutine:
    guild_data = event.data

    roles = guild_data.pop('roles', [])

    objects = [
        DiscordObject(
            id=guild_data['id'],
            data=guild_data
        ),
        *[
            DiscordObject(
                id=role['id'],
                guild_id=guild_data['id'],
                data=role
            )
            for role in roles
        ]
    ]

    async with BulkWriter() as writer:
        for obj in objects:
            await obj.find_one(
                {'_id': obj.id},
                upsert=True
            ).replace_one(obj, bulk_writer=writer)

        return writer.commit()


async def discord_object_sync(event: GatewayEvent) -> None:
    # ? data is removed from the event in processing
    event = deepcopy(event)

    match event.name:
        case GatewayEventName.INTERACTION_CREATE:
            return None
        case GatewayEventName.GUILD_CREATE:
            tasks = [await _guild_create(event)]
        case GatewayEventName.GUILD_UPDATE:
            tasks = [await _guild_update(event)]
        case GatewayEventName.GUILD_DELETE:
            ...
        case GatewayEventName.MESSAGE_CREATE:
            tasks = [
                await _message_create(event),
                await _sync_member(event),
                await _sync_user(event, False)]
        case GatewayEventName.MESSAGE_UPDATE:
            tasks = [
                await _message_update(event),
                await _sync_member(event),
                await _sync_user(event, False)]
        case GatewayEventName.MESSAGE_DELETE:
            tasks = [await _message_delete(event)]
        case GatewayEventName.MESSAGE_REACTION_ADD:
            tasks = [
                await _message_reaction_add(event),
                await _sync_member(event)]
        case GatewayEventName.MESSAGE_REACTION_REMOVE:
            tasks = [await _message_reaction_remove(event)]
        case GatewayEventName.CHANNEL_CREATE:
            tasks = [await _channel_create(event)]
        case GatewayEventName.CHANNEL_UPDATE:
            tasks = [await _channel_update(event)]
        case GatewayEventName.CHANNEL_DELETE:
            tasks = [await _channel_delete(event)]
        case _:
            # print(event.name, dumps(event.data))
            tasks = []

    tasks = [
        task
        for task in tasks
        if task is not None
    ]

    if tasks:
        await gather(*tasks)
