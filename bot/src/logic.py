from dataclasses import dataclass
from types import CoroutineType
from datetime import timedelta
from typing import Self, Any
from hashlib import sha256
from asyncio import gather
from random import randint
from time import time_ns
from io import BytesIO

from regex import match, finditer, escape, sub, IGNORECASE
from beanie import PydanticObjectId
from orjson import dumps

from plural.errors import PluralExceptionCritical, HTTPException, Unauthorized
from plural.db.enums import AutoProxyMode, ReplyFormat
from plural.otel import span, cx
from plural.db import (
    ProxyMember,
    Usergroup,
    AutoProxy,
    ProxyLog,
    Message,
    Group,
    redis
)

from .http import Route, request, File, bytes_to_base64_data, GENERAL_SESSION
from .permission import Permission
from .cache import Cache
from .models import env


EMOJI_SHARDS = 10


@dataclass
class ProxyData:
    member: ProxyMember
    autoproxy: AutoProxy | None
    content: str
    reason: str
    group: Group
    tag: ProxyMember.ProxyTag | None = None
    traceparent: str | None = None

    @property
    def avatar_url(self) -> str | None:
        return (
            (self.tag.avatar_url if self.tag is not None else None) or
            self.member.avatar_url or
            self.group.avatar_url
        )

    @property
    def last_member_string(self) -> str:
        return ''.join([
            str(self.member.id),
            str(self.member.proxy_tags.index(self.tag))
            if self.tag is not None else '99'
        ])


@dataclass
class CheckMemberResult:
    content: str
    proxy_tag: int
    reason: str


@dataclass(frozen=True)
class ProbableEmoji:
    name: str
    id: int
    animated: bool

    def __str__(self) -> str:
        return f'<{'a' if self.animated else ''}:{self.name}:{self.id}>'

    async def read(self) -> bytes:
        async with GENERAL_SESSION.get(
            f'https://cdn.discordapp.com/emojis/{self.id}.{'gif' if self.animated else 'png'}'
        ) as response:

            if response.ok:
                return await response.read()

            raise HTTPException(f'Failed to fetch emoji: {response.status}')


@dataclass
class ClonedEmoji:
    id: int
    token: str

    async def delete(self) -> None:
        await request(Route(
            'DELETE',
            '/applications/{application_id}/emojis/{emoji_id}',
            token=self.token,
            emoji_id=self.id
        ))


@dataclass
class ProxyResult:
    success: bool
    emojis: list[ClonedEmoji]


@dataclass
class ProxyResponse:
    success: bool
    endpoint: str
    json: dict
    params: dict
    token: str
    publish_latency: bool = True

    @classmethod
    def failure(cls, publish_latency: bool) -> Self:
        return cls(False, '', {}, {}, '', publish_latency)


_emoji_index = randint(0, 999)


def emoji_index() -> str:
    global _emoji_index
    if _emoji_index == 999:
        _emoji_index = -1
    _emoji_index += 1
    return f'{_emoji_index:03}'


async def save_debug_log(
    event: dict,
    debug_log: list[str],
    *additional_ids: str
) -> None:
    if not debug_log:
        raise ValueError('No debug log to save.')

    if env.dev:
        print(event['id'], debug_log)  # noqa: T201

    debug_log.insert(0, event['author']['id'])

    log_dump = dumps(debug_log)

    pipeline = redis.pipeline()
    pipeline.hset(
        'proxy_debug',
        mapping={
            event['id']: log_dump,
            **{
                id: log_dump
                for id in additional_ids}})
    pipeline.hexpire(
        'proxy_debug',
        timedelta(hours=1),
        *(event['id'], *additional_ids)
    )

    await pipeline.execute()


async def delete_emojis(
    emojis: list[ClonedEmoji]
) -> None:
    if not emojis:
        return

    # ? move to new object, so if (and when) this function is called again
    # ? it won't try to delete them a second time
    copy = [
        emojis.pop()
        for _ in range(len(emojis))
    ]

    with span(f'deleting {len(copy)} emojis'):
        await gather(*[
            emoji.delete()
            for emoji in
            copy
        ])


def check_member(
    event: dict,
    member: ProxyMember,
    debug_log: list[str]
) -> CheckMemberResult | None:
    for index, proxy_tag in enumerate(member.proxy_tags):
        if not proxy_tag.prefix and not proxy_tag.suffix:
            continue

        prefix, suffix = (
            (proxy_tag.prefix, proxy_tag.suffix)
            if proxy_tag.regex else
            (escape(proxy_tag.prefix), escape(proxy_tag.suffix))
        )

        try:
            check = match(
                f'^({prefix})([\\s\\S]*)({suffix})$',
                event['content'],
                IGNORECASE if not proxy_tag.case_sensitive else 0,
                timeout=0.0005)
        except TimeoutError:
            debug_log.append(
                'Regex timeout on proxy tag '
                f'{proxy_tag.prefix}text{proxy_tag.suffix}.')
            continue

        if (
            check is None or
            not (check.group(2) or event.get('attachments'))
        ):
            continue

        # ? ensure mentions are preserved
        for safety_match in finditer(
            r'<(?:(?:[@#]|sound:|:[\S_]+|\/(?:\w+ ?){1,3}:)\d+|https?:\/\/[^\s]+)>',
            check.string
        ):
            if (
                (check.end(1) and safety_match.start() < check.end(1)) or
                ((check.start(3)-len(check.string)) and
                    safety_match.end() > check.start(3)
                 )
            ):
                break
        else:
            return CheckMemberResult(
                content=check.group(2),
                proxy_tag=index,
                reason=''.join([
                    'Matched proxy tag ',
                    f'`{proxy_tag.prefix}`' if proxy_tag.prefix else '',
                    '​`text`​',  # ? zero width spaces to separate markdown
                    f'`{proxy_tag.suffix}`' if proxy_tag.suffix else '',
                ])
            )

    return None


async def get_proxy_data(
    event: dict,
    debug_log: list[str]
) -> ProxyData | None:
    autoproxies = {
        autoproxy.guild: autoproxy
        for autoproxy in await AutoProxy.find({
            'user': int(event['author']['id']),
            'guild': {'$in': [int(event['guild_id']), None]},
        }).to_list()
    }

    autoproxy = autoproxies.get(
        int(event['guild_id'])
    ) or autoproxies.get(None)
    autoproxy_member: ProxyMember | None = None

    if autoproxy:
        member = await ProxyMember.get(autoproxy.member)
        debug_log.append(
            f'{'Server' if autoproxy.guild else 'Global'} '
            'Autoproxy found ' + (
                'with no member'
                if member is None else
                f'for {member.name}'
            )
        )
    else:
        debug_log.append(
            'No autoproxy found'
        )

    if event.get('__plural_member') is not None:
        debug_log.append(
            'Reproxy command used.'
        )

        member = await ProxyMember.get(PydanticObjectId(event['__plural_member']))

        if member is not None:
            group = await member.get_group()

            proxy_tag = None
            tag_index: int | None = event['__plural_proxy_tag']

            if tag_index is not None:
                proxy_tag = member.proxy_tags[tag_index]

            return ProxyData(
                member=member,
                autoproxy=autoproxy,
                content=event['content'],
                reason='Reproxy command',
                group=group,
                tag=proxy_tag,
                traceparent=event.get('__plural_traceparent')
            )

        debug_log.append(
            'Reproxy member not found.'
        )

    usergroup = await Usergroup.find_one({
        'users': int(event['author']['id'])
    })

    if usergroup is None:
        debug_log.append(
            'User has not registered with /plu/ral.')
        return None

    groups = await Group.find({
        '$or': [
            {'accounts': usergroup.id},
            {'users': int(event['author']['id'])}]
    }).to_list()

    if not groups:
        debug_log.append(
            'No groups found for account.')
        return None

    if (
        autoproxy and
        autoproxy.mode == AutoProxyMode.LOCKED and
        (member := await ProxyMember.get(autoproxy.member))
    ):
        group = next(
            group
            for group in groups
            if member.id in group.members
        )

        return ProxyData(
            member=member,
            autoproxy=autoproxy,
            content=event['content'],
            reason='Locked autoproxy',
            group=group
        )

    recent_members = await ProxyMember.find({
        '_id': {'$in': [
            PydanticObjectId(member_id)
            for member_id in
            await redis.zrange(
                f'recent_proxies:{event['author']['id']}',
                0, -1,
                desc=True
            )]}
    }).to_list()

    for member in recent_members:
        if autoproxy and autoproxy.member == member.id:
            autoproxy_member = member

        if (result := check_member(event, member, debug_log)) is not None:
            group = next(
                (group
                 for group in groups
                 if member.id in group.members),
                None
            )

            if group is None:
                debug_log.append(
                    f'Member `{member.name}` not in any group. This should not happen.')
                continue

            return ProxyData(
                member=member,
                autoproxy=autoproxy,
                content=result.content,
                reason=result.reason,
                group=group,
                tag=member.proxy_tags[result.proxy_tag]
            )

    channel_ids: set[int] = {
        int(event['channel_id'])
    }

    channel = await Cache.get(f'discord:channel:{event['channel_id']}')

    while channel is not None:
        parent_id = channel.data.get('parent_id')
        if parent_id is not None:
            channel_ids.add(int(parent_id))
            break

        channel = await Cache.get(f'discord:channel:{parent_id}')

    for group in groups:
        if group.channels and not (channel_ids & group.channels):
            debug_log.append(
                f'Group `{group.name}` is restricted to other channels.')
            continue

        member_ids = group.members - {member.id for member in recent_members}

        if not member_ids:
            continue

        for member in await ProxyMember.find({
            '_id': {'$in': list(member_ids)}
        }).to_list():
            if autoproxy and autoproxy.member == member.id:
                autoproxy_member = member

            if (result := check_member(event, member, debug_log)) is not None:
                return ProxyData(
                    member=member,
                    autoproxy=autoproxy,
                    content=result.content,
                    reason=result.reason,
                    group=group,
                    tag=member.proxy_tags[result.proxy_tag]
                )

    if autoproxy is not None and autoproxy_member is not None:
        group = next(
            group
            for group in groups
            if autoproxy_member.id in group.members
        )

        return ProxyData(
            member=autoproxy_member,
            autoproxy=autoproxy,
            content=event['content'],
            reason=f'{'Server' if autoproxy.guild else 'Global'} Autoproxy',
            group=group
        )

    if autoproxy is None or autoproxy.member is None:
        debug_log.append(
            'No proxy tags found in message.')
        return None

    debug_log.append(
        'Autoproxy is enabled but member not found.'
    )

    return None


async def _new_webhook(
    channel_id: str,
    name: str
) -> dict:
    webhook = await request(
        Route(
            'POST',
            '/channels/{channel_id}/webhooks',
            token=env.bot_token,
            channel_id=channel_id),
        json={
            'name': name
        }
    )

    if webhook.get('url') is None:
        raise ValueError('Webhook creation failed.')

    return webhook


async def get_webhook(
    event: dict,
    use_next: bool,
    webhook_id: str | None = None
) -> dict:
    channel = await Cache.get(f'discord:channel:{event['channel_id']}')

    if channel is None:
        raise ValueError('Channel not found in cache.')

    webhook_index = channel.data.get('__plural_last_webhook', 0)

    if channel.data.get('type') in {11, 12}:
        channel = await Cache.get(
            f'discord:channel:{channel.data['parent_id']}'
        )

        if channel is None:
            raise ValueError('Parent channel not found in cache.')

    channel_id = channel.data.get('id')

    webhooks: list[dict] | None = await redis.json().get(
        f'discord:webhooks:{channel_id}'
    )

    if webhooks is None:
        from .listener import on_webhooks_update

        await on_webhooks_update({
            'channel_id': channel_id,
            'guild_id': event['guild_id']
        }, time_ns())

        webhooks: list[dict] | None = await redis.json().get(
            f'discord:webhooks:{channel_id}'
        )

    if webhook_id is not None:
        webhook = next((
            webhook
            for webhook in webhooks
            if webhook.get('id') == webhook_id
        ), None)

        if webhook is None:
            raise ValueError(f'Webhook with id {webhook_id} not found.')

        return webhook

    if use_next:
        webhook_index += 1

    webhook_index = webhook_index % 2 + 1

    webhook_name = f'/plu/ral proxy {webhook_index}/2'.removesuffix(' 1/2')

    if webhook_index > 2:
        raise ValueError('Webhook index exceeded.')

    webhook = next(
        (webhook
         for webhook in webhooks
         if (
             webhook.get('name') == webhook_name and
             webhook.get('url') is not None
         )),
        {}
    )

    return webhook or await _new_webhook(
        channel_id,
        webhook_name
    )


async def insert_emojis(
    content: str,
    token: str,
    emojis: list[ClonedEmoji],
    force_clone: bool = False
) -> str:
    emojis_used: dict[int, list[ProbableEmoji]] = {}

    for match_ in finditer(r'<(a)?:(\w{2,32}):(\d+)>', content):
        emoji = ProbableEmoji(
            name=str(match_.group(2)),
            id=int(match_.group(3)),
            animated=match_.group(1) is not None
        )

        emojis_used.setdefault(emoji.id % EMOJI_SHARDS, []).append(emoji)

    if not emojis_used:
        return content

    unsharded_used = [
        emoji
        for emojis_ in emojis_used.values()
        for emoji in emojis_
    ]

    if not force_clone:
        pipeline = redis.pipeline()

        for shard, emojis_ in emojis_used.items():
            await pipeline.smismember(
                f'discord_emojis:{shard}',
                *[emoji.id for emoji in emojis_]
            )

        redis_response: list[int] = [
            value
            for response in
            await pipeline.execute()
            for value in response
        ]
    else:
        redis_response = [0] * len([
            emoji
            for emojis_ in emojis_used.values()
            for emoji in emojis_
        ])

    to_clone = [
        emoji
        for emoji, exists in
        zip([
            emoji
            for emojis_ in emojis_used.values()
            for emoji in emojis_
        ], redis_response, strict=True)
        if not exists
    ]

    if not to_clone:
        return content

    app_emojis: dict[int, ProbableEmoji] = {}

    async def _clone_emoji(emoji: ProbableEmoji) -> None:
        response = await request(
            Route(
                'POST',
                '/applications/{application_id}/emojis',
                token=token),
            json={
                'name': f'{emoji.name[:28]}_{emoji_index()}',
                'image': bytes_to_base64_data(await emoji.read())})
        app_emojis[emoji.id] = ProbableEmoji(
            name=response['name'],
            id=int(response['id']),
            animated=response['animated']
        )

    with span(f'cloning {len(to_clone)} emojis'):
        await gather(*[
            _clone_emoji(emoji)
            for emoji in
            to_clone
        ])

    for emoji, exists in zip(unsharded_used, redis_response, strict=True):
        if exists:
            continue

        content = content.replace(
            str(emoji),
            str(app_emojis[emoji.id])
        )

    emojis.extend([
        ClonedEmoji(
            id=emoji.id,
            token=token)
        for emoji in
        app_emojis.values()
    ])

    cx().set_attribute(
        'proxy.cloned_emojis',
        len(emojis)
    )

    return content


def handle_discord_markdown(text: str) -> str:
    markdown_patterns = {
        '*':   r'\*([^*]+)\*',
        '_':   r'_([^_]+)_',
        '**':  r'\*\*([^*]+)\*\*',
        '__':  r'__([^_]+)__',
        '~~':  r'~~([^~]+)~~',
        '`':   r'`([^`]+)`',
        '```': r'```[\s\S]+?```'
    }

    for pattern in markdown_patterns.values():
        text = sub(pattern, r'\1', text)

    for char in [
        '*', '_',
        '~', '`'
    ]:
        text = sub(
            r'(?<!\\)' + escape(char),
            r'\\' + char,
            text
        )

    return text


def parse_allowed_mentions(
    content: str,
    replied_user: bool,
    ignore: set[str]
) -> dict[str, list[str] | bool]:
    parsed = {
        'roles': {
            match.group(1)
            for match in finditer(r'<@&(\d+)>', content)},
        'users': {
            match.group(1)
            for match in finditer(r'<@!?(\d+)>', content)
        }
    }

    for snowflake in ignore:
        parsed['roles'].discard(snowflake)
        parsed['users'].discard(snowflake)

    return {
        'parse': ['everyone'],
        'roles': list(parsed['roles']),
        'users': list(parsed['users']),
        'replied_user': replied_user
    }


def format_reply(
    proxy_content: str,
    reference: dict[str, Any],
    format: ReplyFormat
) -> tuple[str | dict | None, set[str]]:
    if format == ReplyFormat.NONE:
        return None, set()

    content = reference.get('content', '')

    jump_url = (
        'https://discord.com/channels'
        f'/{reference['guild_id']}'
        f'/{reference['channel_id']}'
        f'/{reference['id']}'
    )

    display_name = (
        reference['author']['global_name'] or
        reference['author']['username']
    )

    match format:
        case ReplyFormat.INLINE:
            mention = (
                f'<@{reference['author']['id']}>'
                if reference.get('webhook_id') is None else
                f'`@{display_name}`'
            )

            if match(
                r'^-# \[↪\]\(<https:\/\/discord\.com\/channels\/\d+\/\d+\/\d+>\)',
                content
            ):
                content = '\n'.join(
                    content.split('\n')[1:]
                )

            content = content.replace('\n', ' ')

            # ? add zero-width space to prevent link previews
            content = handle_discord_markdown(
                content
                if len(content) <= 75 else
                f'{content[:75].strip()}…'
            ).replace('://', ':/​/')

            content = (
                content
                if content else
                f'[*Click to see attachment*](<{jump_url}>)'
                if reference.get('attachments') else
                f'[*Click to see message*](<{jump_url}>)'
            )

            proxy_content = f'-# [↪](<{jump_url}>) {mention} {content}\n{proxy_content}'

            if len(proxy_content) > 2000:
                return format_reply(
                    '',
                    reference,
                    ReplyFormat.EMBED
                )

            return (
                proxy_content,
                set(parse_allowed_mentions(
                    content, False, set()
                )['users']))
        case ReplyFormat.EMBED:
            content = (
                content
                if len(content) <= 75 else
                f'{content[:75].strip()}…'
            )

            avatar_url = (
                ('https://cdn.discordapp.com/avatars'
                 f'/{reference['author']['id']}'
                 f'/{reference['author']['avatar']}'
                 f'.{'gif'if reference['author']['avatar'].startswith('a_') else 'png'}'
                 ) if reference['author']['avatar'] else
                ('https://cdn.discordapp.com/embed/avatars'
                 f'/{(
                     (int(reference['author']['id']) >> 22) % 6
                     if reference['author']['discriminator'] in {None, '0000', '0'} else
                     int(reference['author']['discriminator']) % 5)}'
                 )
            )

            return {
                'author': {
                    'name': f'{display_name} ↩️',
                    'icon_url': avatar_url},
                'color': 0x7289da,
                'description': (
                    f'{'✉️ ' if reference.get('attachments') else ''}'
                    f'**[Reply to:]({jump_url})** {content}'
                    if content.strip() else
                    f'*[click to see attachment{'' if len(reference.get('attachments', []))-1 else 's'}]({jump_url})*'
                    if reference.get('attachments') else
                    f'*[click to see message]({jump_url})*'
                )
            }, set()

    return None, set()


async def create_request(
    endpoint: str,
    token: str,
    json: dict,
    params: dict,
    attachments: list[dict]
) -> CoroutineType[Any, Any, dict[str, Any] | str | None]:
    if not attachments:
        return request(
            Route(
                'POST',
                endpoint,
                token=token),
            json=json,
            params=params
        )

    files = [
        File(
            data=BytesIO(await (
                await GENERAL_SESSION.get(
                    attachment['url'])).read()),
            filename=attachment['filename'],
            description=attachment.get('description'),
            spoiler=attachment['filename'].startswith('SPOILER_'),
            duration_secs=attachment.get('duration_secs'),
            waveform=attachment.get('waveform'))
        for attachment in attachments
    ]

    form, json_files = [], []
    for index, file in enumerate(files):
        json_files.append(file.as_payload(index))
        form.append(file.as_form(index))

        if file.is_voice_message:  # ? is_voice_message flag
            json['flags'] = (
                (json.get('flags', 0) or 0) | 1 << 13
            )

    json['attachments'] = json_files
    form.insert(0, {
        'name': 'payload_json',
        'value': dumps(json).decode()
    })

    return request(
        Route(
            'POST',
            endpoint,
            token=token),
        files=files,
        form=form,
        params=params
    )


async def _process_proxy(
    event: dict,
    start_time: int,
    is_edit: bool,
    emojis: list[ClonedEmoji]
) -> ProxyResult:
    publish_latency = not is_edit
    debug_log: list[str] = []

    if not (
        event.get('content') or
        event.get('attachments') or
        event.get('poll')
    ):
        debug_log.append(
            'No content, attachments, or poll present in message.'
        )

        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    if event.get('sticker_items'):
        debug_log.append(
            'Stickers are not supported.')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    if event.get('poll'):
        debug_log.append(
            'Poll support coming later.')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    proxy = await get_proxy_data(event, debug_log)

    if proxy is None:
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    if proxy.reason == 'Reproxy command':
        publish_latency = False

    if event.get('attachments'):
        publish_latency = False

    if proxy.autoproxy is not None:
        if event['content'].startswith('\\'):
            # ? if autoproxy is enabled and,
            # ? if message starts with single backslash, skip proxying this message,
            # ? if message starts with double backslash, reset member on autoproxy

            if event['content'].startswith('\\\\'):
                proxy.autoproxy.member = None
                await proxy.autoproxy.save()

            debug_log.append(
                'Message starts with backslash, skipping proxy.')
            await save_debug_log(event, debug_log)
            return ProxyResult(False, emojis)

        if (
            proxy.member.id != proxy.autoproxy.member and
            proxy.autoproxy.mode == AutoProxyMode.LATCH
        ):
            proxy.autoproxy.member = proxy.member.id
            await proxy.autoproxy.save()

    permission = await Permission.for_member(
        event,
        debug_log,
        str(env.application_id)
    )

    if not permission & Permission.SEND_MESSAGES:
        debug_log.append(
            '/plu/ral cannot send messages in this channel.')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    if not permission & Permission.MANAGE_MESSAGES:
        debug_log.append(
            '/plu/ral cannot delete messages in this channel.')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    if not permission & Permission.MANAGE_WEBHOOKS:
        debug_log.append(
            '/plu/ral cannot create webhooks in this channel.')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    if len(proxy.content) > 2000:
        debug_log.append(
            '/plu/ral cannot send messages longer than 2000 characters.')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    guild = await Cache.get(f'discord:guild:{event['guild_id']}')

    channel = await Cache.get(f'discord:channel:{event['channel_id']}')

    if guild is None:  # ? should never happen if permission passed
        debug_log.append(
            'Guild not found in cache.')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    match guild.data.get('premium_tier'):
        case 0 | 1 | None:
            filesize_limit = 10_485_760
        case 2:
            filesize_limit = 52_428_800
        case 3:
            filesize_limit = 104_857_600
        case _:
            filesize_limit = 10_485_760

    total_filesize = sum(
        attachment.get('size', 0)
        for attachment in
        event.get('attachments', [])
    )

    if total_filesize > filesize_limit:
        debug_log.append(
            f'Attachments exceed {filesize_limit / 1048576} MB. '
            f'({total_filesize / 1048576} MB)')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    if total_filesize > 20_971_520:
        debug_log.append(
            'Only 20MB of attachments can be proxied at a time.')
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    userproxy = bool(
        proxy.member.userproxy and
        int(event['guild_id']) in proxy.member.userproxy.guilds
    )

    with span(  # ? only start the span once we're likely proxying
        'proxying message',
        start_time=start_time,
        parent=proxy.traceparent,
        attributes={
            'proxy.member.id': str(proxy.member.id),
            'proxy.member.name': proxy.member.name,
            'proxy.autoproxy': (
                ('guild' if proxy.autoproxy.guild else 'global')
                if proxy.autoproxy else 'none'),
            'proxy.reason': proxy.reason,
            'proxy.user.id': event['author']['id'],
            'proxy.user.name': event['author']['username'],
            'proxy.cloned_emojis': 0
        }
    ):
        await redis.set(
            f'pending_proxy:{event['id']}',
            '1', ex=timedelta(seconds=30)
        )

        handlers = ({
            'userproxy': userproxy_handler,
            'webhook': webhook_handler
        } if userproxy else {
            'webhook': webhook_handler
        })

        original_deleted = False

        await ProxyLog(
            author_id=int(event['author']['id']),
            message_id=int(event['id']),
            author_name=event['author']['username'],
            channel_id=int(event['channel_id']),
            content=sha256(event['content'].encode()).hexdigest()
        ).save()

        for name, handler in handlers.items():
            response = await handler(
                event, proxy, debug_log, emojis
            )

            if response.publish_latency is False:
                publish_latency = False

            if not response.success:
                continue

            tasks = [await create_request(
                response.endpoint,
                response.token,
                response.json,
                response.params,
                event.get('attachments', [])
            )]

            if not original_deleted:
                tasks.insert(0, request(
                    Route(
                        'DELETE',
                        '/channels/{channel_id}/messages/{message_id}',
                        token=env.bot_token,
                        channel_id=event['channel_id'],
                        message_id=event['id']),
                    reason='/plu/ral proxy'
                ))

            discord_responses = await gather(
                *tasks,
                return_exceptions=True
            )

            match discord_responses:
                case (BaseException(), BaseException()):
                    debug_log.append(
                        'Failed to delete message and send proxy.')
                    await save_debug_log(event, debug_log)
                    return ProxyResult(False, emojis)
                case (BaseException(), message):
                    await request(Route(
                        'DELETE',
                        '/channels/{channel_id}/messages/{message_id}',
                        token=env.bot_token,
                        channel_id=event['channel_id'],
                        message_id=message['id']))
                    debug_log.append(
                        'Failed to delete original message.')
                    return ProxyResult(False, emojis)
                case (_delete, BaseException()):
                    await delete_emojis(emojis)
                    original_deleted = True

                    if name == 'webhook':
                        raise PluralExceptionCritical(
                            'Proxy deleted original message but failed to send proxy.'
                        ) from discord_responses[1]
                case (_delete, message):
                    debug_log.append(
                        'Successfully proxied message.')
                    cx().update_name(f'proxying message ({name})')
                    break
        else:
            raise RuntimeError(
                'Proxy handlers failed but did not raise an exception.',
                str(debug_log)
            )

        await Message(
            original_id=int(event['id']),
            proxy_id=int(message['id']),
            author_id=int(event['author']['id']),
            channel_id=int(event['channel_id']),
            member_id=proxy.member.id,
            reason=proxy.reason,
            webhook_id=message.get('webhook_id'),
        ).save()

        pipeline = redis.pipeline()

        latency = (
            ((int(message['id']) >> 22) + 1420070400000) -
            ((int(event['id']) >> 22) + 1420070400000)
        )

        cx().set_attribute('proxy.latency', latency)

        if proxy.reason != 'Reproxy command':
            debug_log.append(f'Latency: {latency}ms')

        if publish_latency and not emojis:
            pipeline.lpush('proxy_latency', latency)
            pipeline.ltrim('proxy_latency', 0, 99)

        pipeline.zadd(
            f'recent_proxies:{event['author']['id']}',
            {str(proxy.member.id): 1},
            incr=True)
        pipeline.expire(
            f'recent_proxies:{event['author']['id']}',
            timedelta(days=1), nx=True)

        if name == 'webhook':
            pipeline.json().set(
                f'discord:channel:{event["channel_id"]}',
                '$.data.__plural_last_member',
                proxy.last_member_string)

            if channel.data.get('__plural_last_member') != proxy.last_member_string:
                pipeline.json().numincrby(
                    f'discord:channel:{event["channel_id"]}',
                    '$.data.__plural_last_webhook',
                    1
                )

        await gather(
            pipeline.execute(),
            # ? delete emojis here so they're a child of this span
            delete_emojis(emojis),
            save_debug_log(event, debug_log, message['id']))
        return ProxyResult(True, emojis)


async def webhook_handler(
    event: dict,
    proxy: ProxyData,
    _debug_log: list[str],
    emojis: list[ClonedEmoji]
) -> ProxyResponse:
    original_content = proxy.content

    channel = await Cache.get(
        f'discord:channel:{event['channel_id']}'
    )

    webhook = await get_webhook(
        event,
        channel.data.get('__plural_last_member') != proxy.last_member_string
    )

    if webhook.get('application_id', '1') is not None:
        # ? webhooks created by users don't need emojis cloned
        proxy.content = await insert_emojis(
            proxy.content,
            env.bot_token,
            emojis
        )

    embeds = []
    mention_ignore = set()

    if event.get('referenced_message') is not None:
        usergroup = await Usergroup.get_by_user(int(event['author']['id']))

        reply, mention_ignore = format_reply(
            proxy.content,
            event['referenced_message'] | {'guild_id': event['guild_id']},
            usergroup.config.reply_format
        )

        match reply:
            case str():
                proxy.content = reply
            case dict():
                embeds.append(reply)

    params = {
        'wait': 'true'
    }

    if channel.data.get('type') in {11, 12}:
        params['thread_id'] = event['channel_id']

    return ProxyResponse(
        success=True,
        endpoint=f'/webhooks/{webhook['id']}/{webhook['token']}',
        json={
            'content': proxy.content,
            'username': ' '.join([proxy.member.name, (proxy.group.tag or '')]),
            'avatar_url': proxy.avatar_url,
            'allowed_mentions': parse_allowed_mentions(
                original_content,
                (
                    event.get('referenced_message') is not None and
                    event.get('referenced_message')['author']['id'] in [
                        user['id']
                        for user in event.get('mentions', [])]),
                mention_ignore),
            'embeds': embeds},
        params=params,
        token=env.bot_token,
        publish_latency=True
    )


async def userproxy_handler(
    event: dict,
    proxy: ProxyData,
    debug_log: list[str],
    emojis: list[ClonedEmoji]
) -> ProxyResponse:
    publish_latency = True

    if proxy.tag and proxy.tag.avatar:
        debug_log.append(
            'Avatar proxy tag used, falling back to webhook.')
        return ProxyResponse.failure(publish_latency)

    member = await Cache.get(
        f'discord:member:{event['guild_id']}:{proxy.member.userproxy.bot_id}'
    )

    if member is None:
        publish_latency = False
        with span('userproxy guild member not in cache'):
            member = await Cache(
                await request(Route(
                    'GET',
                    '/guilds/{guild_id}/members/{user_id}',
                    token=env.bot_token,
                    guild_id=event['guild_id'],
                    user_id=proxy.member.userproxy.bot_id)),
                [], False, 0
            ).save(
                f'discord:member:{event['guild_id']}:{proxy.member.userproxy.bot_id}',
                timedelta(minutes=10)
            )

        debug_log.append(
            'Userproxy member not found in cache. Fetching...'
        )

    member_permissions = await Permission.for_member(
        event,
        debug_log,
        str(proxy.member.userproxy.bot_id)
    )

    if not member_permissions & Permission.VIEW_CHANNEL:
        debug_log.append(
            'Userproxy bot cannot view this channel.')
        return ProxyResponse.failure(publish_latency)

    if not member_permissions & Permission.SEND_MESSAGES:
        debug_log.append(
            'Userproxy bot cannot send messages in this channel.')
        return ProxyResponse.failure(publish_latency)

    try:
        proxy.content = await insert_emojis(
            proxy.content,
            proxy.member.userproxy.token,
            emojis,
            force_clone=True)
    except Unauthorized:
        debug_log.append(
            'Userproxy bot token is invalid or expired.')
        return ProxyResponse.failure(publish_latency)

    return ProxyResponse(
        success=True,
        endpoint=f'/channels/{event['channel_id']}/messages',
        json={
            'content': proxy.content,
            'message_reference': {
                **event['message_reference'],
                'fail_if_not_exists': False
            } if event.get('message_reference') else None,
            'allowed_mentions': {'replied_user': (
                event.get('referenced_message') is not None and
                event.get('referenced_message')['author']['id'] in [
                    user['id']
                    for user in event.get('mentions', [])])},
            'flags': (  # ? suppress only if suppress was not already there
                1 << 12  # ? suppress notifications
                & int(event.get('flags', 0)) ^
                1 << 12  # ? suppress notifications
            ) if event.get('mentions') else None},
        params={},
        token=proxy.member.userproxy.token,
        publish_latency=publish_latency
    )


async def process_proxy(
    event: dict,
    start_time: int,
    is_edit: bool
) -> ProxyResult:
    emojis = []
    try:
        result = await _process_proxy(
            event,
            start_time,
            is_edit,
            emojis
        )

        await delete_emojis(emojis)

        return result
    except BaseException as e:
        await delete_emojis(emojis)
        raise e
