from src.discord import GatewayEvent, GatewayEventName
from datetime import datetime, UTC
from asyncio import gather, sleep
from src.db import DiscordCache
from pymongo import UpdateOne
from typing import Coroutine
from copy import deepcopy

# ? this entire file is mildly gross, please do not look at it


def now() -> str:
    return datetime.now(UTC).isoformat()


def Set(
    dict: dict,
    set_defaults: bool = True,
    set_guild: bool = True,
    set_deleted: bool = True
) -> dict:
    if not set_defaults:
        return {'$set': dict}

    if set_guild:
        dict.setdefault('guild_id', None)

    if set_deleted:
        dict.setdefault('deleted', False)

    dict.setdefault('ts', now())

    return {
        '$set': dict
    }


def _member_update(event: GatewayEvent) -> UpdateOne | None:
    if event.data.get('webhook_id', None) is not None:
        return None

    member_data = event.data['member']

    member_data.pop('user', None)
    user_id = event.data.get(
        'user_id', None
    ) or (
        event.data['author']['id']
    )

    return UpdateOne(
        {'snowflake': int(user_id), 'guild_id': int(event.data['guild_id'])},
        Set({
            'snowflake': int(user_id),
            'guild_id': int(event.data['guild_id']),
            'data': {
                '$mergeObjects': [
                    {'$ifNull': ['$data', {}]},
                    member_data
                ]}}),
        upsert=True
    )


def _user_update(event: GatewayEvent) -> UpdateOne:
    user_data = (
        event.data['author']
        if 'author' in event.data else
        event.data['member']['user']
        if 'member' in event.data else
        event.data['user']
    )

    return UpdateOne(
        {'snowflake': int(user_data['id']), 'guild_id': None},
        Set({
            'snowflake': int(user_data['id']),
            'data': {
                '$mergeObjects': [
                    {'$ifNull': ['$data', {}]},
                    user_data
                ]}}),
        upsert=True
    )


def guild_create_update(event: GatewayEvent) -> Coroutine:
    guild_data = event.data

    members = guild_data.pop('members', [])

    users = [
        member.pop('user', True)
        for member in
        members
        # ? set user id on member object, popped when saving
        if member.update({'user_id': member['user']['id']})
    ]

    roles = guild_data.pop('roles', [])

    channels = guild_data.pop('channels', [])

    channels.extend(guild_data.pop('threads', []))

    emojis = guild_data.pop('emojis', [])

    return DiscordCache.get_motor_collection().bulk_write(
        [
            UpdateOne(
                {'snowflake': int(snowflake), 'guild_id': guild_id},
                [Set({
                    'snowflake': int(snowflake),
                    'guild_id': guild_id,
                    'data': {
                        '$mergeObjects': [
                            {'$ifNull': ['$data', {}]},
                            data
                        ]}})],
                upsert=True)
            for snowflake, data, guild_id in (
                (guild_data['id'], guild_data, None),
                *(
                    (member.pop('user_id'), member, None)
                    for member in members
                ), *(
                    (user['id'], user, int(guild_data['id']))
                    for user in users
                ), *(
                    (role['id'], role, int(guild_data['id']))
                    for role in roles
                ), *(
                    (channel['id'], channel, int(guild_data['id']))
                    for channel in channels
                ), *(
                    (emoji['id'], emoji, int(guild_data['id']))
                    for emoji in emojis
                )
            )
        ]
    )


def guild_delete(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_many({
        '$or': [
            {'guild_id': int(event.data['id'])},
            {'snowflake': int(event.data['id'])}]},
        Set({
            'deleted': True,
            'data': event.data
        }, set_guild=False)
    )


def guild_role_create_update(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['role']['id'])},
        Set({
            'snowflake': int(event.data['role']['id']),
            'guild_id': int(event.data['guild_id']),
            'data': {
                '$mergeObjects': [
                    {'$ifNull': ['$data', {}]},
                    event.data['role']
                ]}}),
        upsert=True
    )


def guild_role_delete(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['role_id'])},
        Set({
            'snowflake': int(event.data['role_id']),
            'deleted': True,
            'data': event.data}),
        upsert=True
    )


def channel_thread_create_update(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['id'])},
        Set({
            'snowflake': int(event.data['id']),
            'guild_id': int(event.data['guild_id']),
            'data': {
                '$mergeObjects': [
                    {'$ifNull': ['$data', {}]},
                    event.data
                ]}}),
        upsert=True
    )


def channel_thread_delete(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['id'])},
        Set({
            'snowflake': int(event.data['id']),
            'deleted': True,
            'data': event.data}),
        upsert=True
    )


def thread_list_sync(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().bulk_write(
        [
            UpdateOne(
                {'snowflake': int(snowflake), 'guild_id': guild_id},
                Set({
                    'snowflake': int(snowflake),
                    'guild_id': guild_id,
                    'data': {
                        '$mergeObjects': [
                            {'$ifNull': ['$data', {}]},
                            data
                        ]}}),
                upsert=True)
            for snowflake, data, guild_id in (
                (channel['id'], channel, int(event.data['guild_id']))
                for channel in event.data['threads']
            )
        ]
    )


def message_create_update(event: GatewayEvent) -> Coroutine:
    requests = [
        UpdateOne(
            {'snowflake': int(event.data['id'])},
            [Set({
                'snowflake': int(event.data['id']),
                'data': {
                    '$mergeObjects': [
                        {'$ifNull': ['$data', {}]},
                        event.data, {
                            'content': '',
                            'attachments': []
                        }
                    ]
                }
            }), Set({
                    'data.referenced_message': {
                        '$cond': {
                            'if': {'$ifNull': ['$$ROOT.data.referenced_message', False]},
                            'then': {
                                '$mergeObjects': [
                                    '$data.referenced_message', {
                                        'content': '',
                                        'attachments': []
                                    }]},
                            'else': '$$REMOVE'
                        }
                    }
                    }, False)],
            upsert=True
        ),
        _user_update(event)
    ]

    member = _member_update(event)

    if member is not None:
        requests.append(member)

    return DiscordCache.get_motor_collection().bulk_write(
        requests
    )


def message_delete(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['id'])},
        Set({
            'snowflake': int(event.data['id']),
            'deleted': True,
            'data': event.data}),
        upsert=True
    )


def message_delete_bulk(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().bulk_write(
        [
            UpdateOne(
                {'snowflake': int(snowflake)},
                Set({
                    'snowflake': int(snowflake),
                    'deleted': True,
                    'data': {
                        'id': snowflake,
                        'channel_id': event.data['channel_id'],
                        'guild_id': event.data['guild_id'], }}),
                upsert=True)
            for snowflake in event.data['ids']
        ]
    )


async def message_reaction_add(event: GatewayEvent) -> Coroutine:
    #! refactor this with new format
    #! also this needs to sync member
    return sleep(0)
    message = await DiscordCache.find_one(
        {'snowflake': int(event.data['message_id'])})

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


async def message_reaction_remove(event: GatewayEvent) -> Coroutine:
    #! refactor this with new format
    return sleep(0)
    message = await DiscordCache.find_one(
        {'snowflake': int(event.data['message_id'])})

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


async def discord_cache(event: GatewayEvent) -> None:
    # ? data is removed from the event in processing
    event = deepcopy(event)

    # from orjson import dumps
    # print(event.name, dumps(event.data))

    match event.name:
        case GatewayEventName.GUILD_CREATE | GatewayEventName.GUILD_UPDATE:
            tasks = [guild_create_update(event)]
        case GatewayEventName.GUILD_DELETE:
            tasks = [guild_delete(event)]
        case GatewayEventName.GUILD_ROLE_CREATE | GatewayEventName.GUILD_ROLE_UPDATE:
            tasks = [guild_role_create_update(event)]
        case GatewayEventName.GUILD_ROLE_DELETE:
            tasks = [guild_role_delete(event)]
        case (
            GatewayEventName.CHANNEL_CREATE | GatewayEventName.CHANNEL_UPDATE |
            GatewayEventName.THREAD_CREATE | GatewayEventName.THREAD_UPDATE
        ):
            tasks = [channel_thread_create_update(event)]
        case GatewayEventName.CHANNEL_DELETE | GatewayEventName.THREAD_DELETE:
            tasks = [channel_thread_delete(event)]
        case GatewayEventName.THREAD_LIST_SYNC:
            tasks = [thread_list_sync(event)]
        case GatewayEventName.GUILD_EMOJIS_UPDATE:
            tasks = []  # TODO
        case GatewayEventName.WEBHOOKS_UPDATE:
            tasks = []  # TODO
        case GatewayEventName.MESSAGE_CREATE | GatewayEventName.MESSAGE_UPDATE:
            tasks = [message_create_update(event)]
        case GatewayEventName.MESSAGE_DELETE:
            tasks = [message_delete(event)]
        case GatewayEventName.MESSAGE_DELETE_BULK:
            tasks = [message_delete_bulk(event)]
        # ? might not even bother with reaction events, since /plu/ral doesn't read them
        case GatewayEventName.MESSAGE_REACTION_ADD:
            tasks = [await message_reaction_add(event)]
        case GatewayEventName.MESSAGE_REACTION_REMOVE:
            tasks = [await message_reaction_remove(event)]
        case GatewayEventName.MESSAGE_REACTION_REMOVE_ALL:
            tasks = []  # TODO
        case GatewayEventName.MESSAGE_REACTION_REMOVE_EMOJI:
            tasks = []  # TODO
        case _:
            return None

    await gather(*tasks)
