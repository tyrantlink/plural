from src.discord import GatewayEvent, GatewayEventName, GatewayOpCode
from src.db import DiscordCache, CacheType
from datetime import datetime, UTC
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
    set_deleted: bool = True,
    skip_missing_check: bool = False
) -> dict:
    missing_keys = {'snowflake', 'data', 'type'} - dict.keys()

    if missing_keys and not skip_missing_check:
        raise ValueError(f'missing required keys: {missing_keys}')

    if isinstance(dict.get('type'), CacheType):
        dict['type'] = dict['type'].value

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


async def _member_update(event: GatewayEvent) -> list[UpdateOne] | None:
    if event.data.get('webhook_id', None) is not None:
        return None

    member_data = event.data['member']

    user = member_data.pop('user', None)

    user_id = (
        user['id']
        if user is not None else
        event.data.get(
            'user_id', None
        ) or (
            event.data['author']['id']
        )
    )

    update = [UpdateOne(
        {'snowflake': int(user_id), 'guild_id': int(event.data['guild_id'])},
        [Set({
            'snowflake': int(user_id),
            'guild_id': int(event.data['guild_id']),
            'type': CacheType.MEMBER,
            'data': {
                '$mergeObjects': [
                    {'$ifNull': ['$data', {}]},
                    member_data
                ]}})],
        upsert=True
    )]

    existing_roles = {
        role['snowflake']
        for role in await (
            await DiscordCache.get_motor_collection().aggregate([
                {  # type: ignore # ? using async pymongo, not motor
                    '$match': {
                        'snowflake': {'$in': [
                            int(role_id)
                            for role_id in
                            member_data['roles']]},
                        'type': CacheType.ROLE.value
                    }
                }, {
                    '$project': {
                        '_id': 0,
                        'snowflake': 1
                    }
                }
            ])
        ).to_list()
    }

    missing_roles = set(member_data['roles']) - existing_roles

    if not missing_roles:
        return update

    from src.discord.http import request, Route

    roles = await request(Route(
        'GET',
        '/guilds/{guild_id}/roles',
        guild_id=int(event.data['guild_id'])
    ))

    return update.extend([
        UpdateOne(
            {'snowflake': int(role['id'])},
            [Set({
                'snowflake': int(role['id']),
                'guild_id': int(event.data['guild_id']),
                'type': CacheType.ROLE,
                'data': {
                    '$mergeObjects': [
                        {'$ifNull': ['$data', {}]},
                        role
                    ]}})],
            upsert=True)
        for role in roles
    ])


async def member_update(dict: dict, guild_id: int) -> None:
    event = GatewayEvent(
        op=GatewayOpCode.DISPATCH, s=0,
        t=GatewayEventName.MESSAGE_CREATE,
        d={'member': dict, 'guild_id': str(guild_id)}
    )

    request = [_user_update(event)]

    update = await _member_update(event)

    if update is not None:
        request.extend(update)

    await DiscordCache.get_motor_collection().bulk_write(
        request
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
        [Set({
            'snowflake': int(user_data['id']),
            'type': CacheType.USER,
            'data': {
                '$mergeObjects': [
                    {'$ifNull': ['$data', {}]},
                    user_data
                ]}})],
        upsert=True
    )


async def user_update(dict: dict) -> None:
    event = GatewayEvent(
        op=GatewayOpCode.DISPATCH, s=0,
        t=GatewayEventName.MESSAGE_CREATE,
        d={'author': dict}
    )

    await DiscordCache.get_motor_collection().bulk_write(
        [_user_update(event)]
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
                    'type': cache_type,
                    'data': {
                        '$mergeObjects': [
                            {'$ifNull': ['$data', {}]},
                            data
                        ]}})],
                upsert=True)
            for snowflake, data, guild_id, cache_type in (
                (guild_data['id'], guild_data, None, CacheType.GUILD),
                *(
                    (member.pop('user_id'), member, None, CacheType.MEMBER)
                    for member in members
                ), *(
                    (user['id'], user, int(guild_data['id']), CacheType.USER)
                    for user in users
                ), *(
                    (role['id'], role, int(guild_data['id']), CacheType.ROLE)
                    for role in roles
                ), *(
                    (channel['id'], channel, int(
                        guild_data['id']), CacheType.CHANNEL)
                    for channel in channels
                ), *(
                    (emoji['id'], emoji, int(guild_data['id']), CacheType.EMOJI)
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
            'type': CacheType.GUILD,
            'data': event.data
        }, set_guild=False)
    )


def guild_role_create_update(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['role']['id'])},
        [Set({
            'snowflake': int(event.data['role']['id']),
            'guild_id': int(event.data['guild_id']),
            'type': CacheType.ROLE,
            'data': {
                '$mergeObjects': [
                    {'$ifNull': ['$data', {}]},
                    event.data['role']
                ]}})],
        upsert=True
    )


def guild_role_delete(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['role_id'])},
        Set({
            'snowflake': int(event.data['role_id']),
            'deleted': True,
            'type': CacheType.ROLE,
            'data': event.data}),
        upsert=True
    )


def channel_thread_create_update(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['id'])},
        [Set({
            'snowflake': int(event.data['id']),
            'guild_id': int(event.data['guild_id']),
            'type': CacheType.CHANNEL,
            'data': {
                '$mergeObjects': [
                    {'$ifNull': ['$data', {}]},
                    event.data
                ]}})],
        upsert=True
    )


def channel_thread_delete(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['id'])},
        Set({
            'snowflake': int(event.data['id']),
            'deleted': True,
            'type': CacheType.CHANNEL,
            'data': event.data}),
        upsert=True
    )


def thread_list_sync(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().bulk_write(
        [
            UpdateOne(
                {'snowflake': int(snowflake), 'guild_id': guild_id},
                [Set({
                    'snowflake': int(snowflake),
                    'guild_id': guild_id,
                    'type': CacheType.CHANNEL,
                    'data': {
                        '$mergeObjects': [
                            {'$ifNull': ['$data', {}]},
                            data
                        ]}})],
                upsert=True)
            for snowflake, data, guild_id in (
                (channel['id'], channel, int(event.data['guild_id']))
                for channel in event.data['threads']
            )
        ]
    )


def guild_emojis_update(event: GatewayEvent) -> Coroutine:
    ...  # TODO


async def webhooks_update(event: GatewayEvent) -> None:
    from src.discord.http import request, Route

    await DiscordCache.get_motor_collection().delete_many({
        'guild_id': int(event.data['guild_id']),
        'data.channel_id': event.data['channel_id'],
        'type': CacheType.WEBHOOK.value
    })

    webhooks = await request(Route(
        'GET',
        '/channels/{channel_id}/webhooks',
        channel_id=int(event.data['channel_id'])
    ))

    await DiscordCache.get_motor_collection().bulk_write([
        UpdateOne(
            {'snowflake': int(webhook['id'])},
            [Set({
                'snowflake': int(webhook['id']),
                'guild_id': int(event.data['guild_id']),
                'type': CacheType.WEBHOOK,
                'data': {
                    '$mergeObjects': [
                        {'$ifNull': ['$data', {}]},
                        webhook
                    ]},
                'ts': None})],
            upsert=True)
        for webhook in webhooks
    ])


async def message_create_update(event: GatewayEvent) -> Coroutine:
    requests = [
        UpdateOne(
            {'snowflake': int(event.data['id'])},
            [Set({
                'snowflake': int(event.data['id']),
                'type': CacheType.MESSAGE,
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
                    }}, skip_missing_check=True)],
            upsert=True
        ),
        _user_update(event)
    ]

    member = await _member_update(event)

    if member is not None:
        requests.extend(member)

    if event.name == GatewayEventName.MESSAGE_CREATE:
        requests.append(UpdateOne({
            'snowflake': int(event.data['channel_id'])
        }, {
            '$max': {
                'data.last_message_id': event.data['id']
            }
        }))

    return DiscordCache.get_motor_collection().bulk_write(
        requests
    )


def message_delete(event: GatewayEvent) -> Coroutine:
    return DiscordCache.get_motor_collection().update_one(
        {'snowflake': int(event.data['id'])},
        Set({
            'snowflake': int(event.data['id']),
            'deleted': True,
            'type': CacheType.MESSAGE,
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
                    'type': CacheType.MESSAGE,
                    'data': {
                        'id': snowflake,
                        'channel_id': event.data['channel_id'],
                        'guild_id': event.data['guild_id'], }}),
                upsert=True)
            for snowflake in event.data['ids']
        ]
    )


async def message_reaction_add(event: GatewayEvent) -> Coroutine:
    # ? i don't actually care about the reaction, just update member data
    requests = []

    if 'user' in event.data['member']:
        requests.append(_user_update(event))

    member = await _member_update(event)

    if member is not None:
        requests.append(member)

    return DiscordCache.get_motor_collection().bulk_write(
        requests
    )


async def discord_cache(event: GatewayEvent) -> None:
    # ? data is removed from the event in processing
    event = deepcopy(event)

    match event.name:
        case GatewayEventName.GUILD_CREATE | GatewayEventName.GUILD_UPDATE:
            task = guild_create_update(event)
        case GatewayEventName.GUILD_DELETE:
            task = guild_delete(event)
        case GatewayEventName.GUILD_ROLE_CREATE | GatewayEventName.GUILD_ROLE_UPDATE:
            task = guild_role_create_update(event)
        case GatewayEventName.GUILD_ROLE_DELETE:
            task = guild_role_delete(event)
        case (
            GatewayEventName.CHANNEL_CREATE | GatewayEventName.CHANNEL_UPDATE |
            GatewayEventName.THREAD_CREATE | GatewayEventName.THREAD_UPDATE
        ):
            task = channel_thread_create_update(event)
        case GatewayEventName.CHANNEL_DELETE | GatewayEventName.THREAD_DELETE:
            task = channel_thread_delete(event)
        case GatewayEventName.THREAD_LIST_SYNC:
            task = thread_list_sync(event)
        case GatewayEventName.GUILD_EMOJIS_UPDATE:
            task = guild_emojis_update(event)
        case GatewayEventName.WEBHOOKS_UPDATE:
            task = webhooks_update(event)
        case GatewayEventName.MESSAGE_CREATE | GatewayEventName.MESSAGE_UPDATE:
            task = await message_create_update(event)
        case GatewayEventName.MESSAGE_DELETE:
            task = message_delete(event)
        case GatewayEventName.MESSAGE_DELETE_BULK:
            task = message_delete_bulk(event)
        case GatewayEventName.MESSAGE_REACTION_ADD:
            task = await message_reaction_add(event)
        case _:
            return None

    await task
