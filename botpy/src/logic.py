from asyncio import gather, sleep, timeout, get_event_loop
from concurrent.futures import ProcessPoolExecutor
from urllib.parse import urlparse, parse_qs
from datetime import timedelta, datetime
from collections.abc import Callable
from dataclasses import dataclass
from contextlib import suppress
from types import CoroutineType
from time import perf_counter
from typing import Self, Any
from hashlib import sha256
from time import time_ns
from io import BytesIO

from regex import match, escape, sub, compile, IGNORECASE
from beanie import PydanticObjectId
from orjson import dumps

from plural.db.enums import AutoproxyMode, ReplyFormat
from plural.otel import span, cx, get_counter, inject
from plural.errors import (
    PluralExceptionCritical,
    PluralException,
    HTTPException,
    Unauthorized,
    Forbidden,
    NotFound
)
from plural.db import (
    ProxyMember,
    Usergroup,
    Autoproxy,
    ProxyLog,
    Message,
    Group,
    Guild,
    redis
)

from .http import Route, request, File, bytes_to_base64_data, GENERAL_SESSION
from .permission import Permission
from .cache import Cache
from .models import env
from .caith import roll


EMOJI_SHARDS = 10
MENTION_PATTERN = compile(
    r'<(?:'  # ? handles when proxy tags are <text> and ensures mentions are preserved
    r'(?:[@#/][!&]?\d+)|'        # ? users, channels, roles
    r'(?:/(?:\w+ ?){1,3}:)\d+|'  # ? slash commands
    r'(?:a?:[^:]+:\d+)|'         # ? custom emoji
    r'(?:t:\d+:[tTdDfFR])|'      # ? timestamps
    r'(?:id:customize)|'         # ? guild navigation
    r'(?:sound:\d+)|'            # ? soundmoji (might be deprecated)
    r'(?:https?://[^\s]+))>')    # ? urls
INLINE_REPLY_PATTERN = compile(
    r'^-# \[↪\]\(<https:\/\/discord\.com\/channels\/\d+\/\d+\/\d+>\) (?:<@(\d+)>)?')
EMOJI_PATTERN = compile(r'<(a)?:(\w{2,32}):(\d+)>')
ROLE_MENTION_PATTERN = compile(r'<@&(\d+)>')
USER_MENTION_PATTERN = compile(r'<@!?(\d+)>')
CHANNEL_MENTION_PATTERN = compile(r'<#(\d+)>')
NQN_EMOJI_PATTERN = compile(
    r'\[.+\]\((https://cdn\.discordapp\.com/emojis/\d+\..+size(?:.+animated)?.+name.+)\)')
BLOCK_PATTERN = compile(r'{{(.+?)}}')


class OverWebhookLimit(PluralException):
    ...


@dataclass
class ProxyData:
    member: ProxyMember
    autoproxy: Autoproxy | None
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


_emoji_index = redis.register_script("""
local current = tonumber(redis.call('GET', KEYS[1]) or 0)
local new_value = (current + 1) % 1000
redis.call('SET', KEYS[1], new_value)
return current
""")


async def emoji_index_init() -> None:
    await redis.set('emoji_index', 0, nx=True)


async def emoji_index() -> str:
    return f'{await _emoji_index(['emoji_index']):03}'


async def to_process[T](
    executor: ProcessPoolExecutor,
    func: Callable[..., T],
    *args  # noqa: ANN002
) -> T:
    return await get_event_loop(
    ).run_in_executor(
        executor,
        func,
        *args
    )


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
            **dict.fromkeys(additional_ids, log_dump)})
    pipeline.hexpire(
        'proxy_debug',
        timedelta(days=1),
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

        mentions = len(MENTION_PATTERN.findall(check.string))

        if mentions:
            proxied_mentions = len(MENTION_PATTERN.findall(check.group(2)))
            if (
                mentions != proxied_mentions and
                mentions != sum((
                    proxied_mentions,
                    len(MENTION_PATTERN.findall(proxy_tag.prefix)),
                    len(MENTION_PATTERN.findall(proxy_tag.suffix))
                ))
            ):
                debug_log.append(
                    f'Proxy tag {proxy_tag.name} '
                    'Failed to preserve all mentions.')
                continue

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
    usergroup = await Usergroup.find_one({
        'users': int(event['author']['id'])
    })

    if usergroup is None:
        debug_log.append(
            'User has not registered with /plu/ral.')
        return None

    autoproxies = {
        autoproxy.guild: autoproxy
        for autoproxy in await Autoproxy.find({
            'user': usergroup.id,
            'guild': {'$in': [int(event['guild_id']), None]},
        }).to_list()
    }

    autoproxy = autoproxies.get(
        int(event['guild_id'])
    ) or autoproxies.get(None)
    autoproxy_members: dict[int | None, ProxyMember] = {}

    if (
        autoproxy and
        autoproxy.mode == AutoproxyMode.DISABLED
    ):
        debug_log.append(
            'Autoproxy mode is "disabled". All proxying is disabled.')
        return None

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

    groups = await Group.find({
        '$or': [
            {'account': usergroup.id},
            {f'users.{event['author']['id']}': {'$exists': True}}]
    }).to_list()

    if not groups:
        debug_log.append(
            'No groups found for account.')
        return None

    channel_ids: set[int] = {
        int(event['channel_id'])
    }

    channel = await Cache.get(f'discord:channel:{event['channel_id']}')

    while channel is not None:
        if (parent_id := channel.data.get('parent_id')) is None:
            break

        channel_ids.add(int(parent_id))

        channel = await Cache.get(f'discord:channel:{parent_id}')

    if (
        autoproxy and
        autoproxy.mode == AutoproxyMode.LOCKED and
        (member := await ProxyMember.get(autoproxy.member))
    ):
        group = next(
            (group
             for group in groups
             if member.id in group.members),
            None
        )

        if group is None:
            debug_log.append(
                f'Member `{member.name}` not in any group. This should not happen.')

        if group and not (group.channels and not (channel_ids & group.channels)):
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
        for autoproxy_ in autoproxies.values():
            if autoproxy_.member == member.id:
                autoproxy_members[autoproxy_.guild] = member

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

            if group.channels and not (channel_ids & group.channels):
                if autoproxy and autoproxy.guild is not None and autoproxies.get(None):
                    debug_log.append(
                        'Autoproxy member restricted to other channels. '
                        'Falling back to global autoproxy.')
                    autoproxy = autoproxies[None]
                continue

            if (
                group.channels and
                autoproxy and
                autoproxy.guild is None and
                autoproxy.member != member.id and
                autoproxies.get(int(event['guild_id'])) is None
            ):
                debug_log.append(
                    'Matched member in restricted group and different from autoproxy. '
                    'Auto-creating server autoproxy.')
                autoproxy = await Autoproxy(
                    user=usergroup.id,
                    guild=int(event['guild_id']),
                    member=member.id,
                    ts=None
                ).save()

            return ProxyData(
                member=member,
                autoproxy=autoproxy,
                content=result.content,
                reason=result.reason,
                group=group,
                tag=member.proxy_tags[result.proxy_tag]
            )

    for group in groups:
        if group.channels and not (channel_ids & group.channels):
            if not any(log.startswith('Channel Stack: ') for log in debug_log):
                debug_log.append(f'Channel Stack: {channel_ids}')
            debug_log.append(
                f'Group `{group.name}` is restricted to other channels.')
            if (
                autoproxy and
                autoproxy.guild is not None and
                autoproxies.get(None) and
                autoproxy.member in group.members
            ):
                debug_log.append(
                    'Server autoproxy member restricted to other channels. '
                    'Falling back to global autoproxy.')
                autoproxy = autoproxies[None]
            continue

        member_ids = group.members - {member.id for member in recent_members}

        if not member_ids:
            continue

        for member in await ProxyMember.find({
            '_id': {'$in': list(member_ids)}
        }).to_list():
            for autoproxy_ in autoproxies.values():
                if autoproxy_.member == member.id:
                    autoproxy_members[autoproxy_.guild] = member

            if (result := check_member(event, member, debug_log)) is not None:
                if (
                    group.channels and
                    autoproxy and
                    autoproxy.guild is None and
                    autoproxy.member != member.id and
                    autoproxies.get(int(event['guild_id'])) is None
                ):
                    debug_log.append(
                        'Matched member in restricted group and different from autoproxy. '
                        'Auto-creating server autoproxy.')
                    autoproxy = await Autoproxy(
                        user=usergroup.id,
                        guild=int(event['guild_id']),
                        member=member.id,
                        ts=None
                    ).save()

                return ProxyData(
                    member=member,
                    autoproxy=autoproxy,
                    content=result.content,
                    reason=result.reason,
                    group=group,
                    tag=member.proxy_tags[result.proxy_tag]
                )

    if autoproxy is not None and autoproxy_members.get(autoproxy.guild) is not None:
        group = next(
            (group
             for group in groups
             if autoproxy_members[autoproxy.guild].id
             in group.members),
            None
        )

        if group is None:
            debug_log.append(
                f'Member `{autoproxy_members[autoproxy.guild].name}` not in any group. This should not happen.'
            )

        if group and not (group.channels and not (channel_ids & group.channels)):
            return ProxyData(
                member=autoproxy_members[autoproxy.guild],
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
        }, time_ns(), True)

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

    if not webhook and len(webhooks) >= 15:
        raise OverWebhookLimit('Webhook limit reached.')

    return webhook or await _new_webhook(
        channel_id,
        webhook_name
    )


async def insert_emojis(
    content: str,
    token: str,
    emojis: list[ClonedEmoji],
    debug_log: list[str],
    force_clone: bool = False
) -> str:
    emojis_used: dict[int, list[ProbableEmoji]] = {}

    for match_ in EMOJI_PATTERN.finditer(content):
        emoji = ProbableEmoji(
            name=str(match_.group(2)),
            id=int(match_.group(3)),
            animated=match_.group(1) is not None
        )

        emojis_used.setdefault(emoji.id % EMOJI_SHARDS, []).append(emoji)

    for match_ in NQN_EMOJI_PATTERN.finditer(content):
        url = urlparse(match_.group(1))
        query = parse_qs(url.query)

        if 'name' not in query:
            continue

        emoji_id = url.path.removeprefix('/emojis/').split('.')[0]

        if not emoji_id.isdigit():
            continue

        emoji = ProbableEmoji(
            name=query['name'][0],
            id=int(emoji_id),
            animated=query.get('animated', [''])[0].lower() == 'true'
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

    if len(to_clone) > 10:
        debug_log.append(
            'Max emoji clone limit (10) reached.')
        to_clone = to_clone[:10]

    app_emojis: dict[int, ProbableEmoji] = {}

    async def _clone_emoji(emoji: ProbableEmoji) -> None:
        response = await request(
            Route(
                'POST',
                '/applications/{application_id}/emojis',
                token=token),
            json={
                'name': f'{emoji.name[:28]}_{await emoji_index()}',
                'image': bytes_to_base64_data(await emoji.read())})
        app_emojis[emoji.id] = ProbableEmoji(
            name=response['name'],
            id=int(response['id']),
            animated=response['animated']
        )

    with span(f'cloning {len(to_clone)} emojis'):
        clone_responses = await gather(*[
            _clone_emoji(emoji)
            for emoji in
            to_clone],
            return_exceptions=True)

        if (count := sum(
            1
            for response in
            clone_responses
            if isinstance(response, BaseException)
        )):
            await delete_emojis([
                ClonedEmoji(
                    id=emoji.id,
                    token=token)
                for emoji in
                app_emojis.values()])
            debug_log.append(f'Failed to clone {count} emoji.')
            return content

    for emoji, exists in zip(unsharded_used, redis_response, strict=True):
        if exists or emoji.id not in app_emojis:
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
        '*':   compile(r'\*([^*]+)\*'),
        '_':   compile(r'_([^_]+)_'),
        '**':  compile(r'\*\*([^*]+)\*\*'),
        '__':  compile(r'__([^_]+)__'),
        '~~':  compile(r'~~([^~]+)~~'),
        '`':   compile(r'`([^`]+)`'),
        '```': compile(r'```[\s\S]+?```')
    }

    for pattern in markdown_patterns.values():
        text = pattern.sub(r'\1', text)

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


def allowed_mentions(
    proxy: ProxyData,
    replied_user: bool
) -> dict[str, list[str] | bool]:
    content, replied_user_id = proxy.content, None

    if (match := INLINE_REPLY_PATTERN.match(content)) is not None:
        content = proxy.content.split('\n', 1)[1]

        if replied_user:
            replied_user_id = match.group(1)

    return {
        'parse': (
            ['everyone']
            if '@everyone' in content or '@here' in content else
            []),
        'roles': list({
            match_.group(1)
            for match_ in ROLE_MENTION_PATTERN.finditer(content)}),
        'users': list({
            match_.group(1)
            for match_ in USER_MENTION_PATTERN.finditer(content)
        } | {replied_user_id} if replied_user_id else set()),
        'replied_user': replied_user
    }


def format_reply(
    proxy_content: str,
    reference: dict[str, Any],
    format: ReplyFormat,
    embed_color: int | None = None
) -> str | dict | None:
    if format == ReplyFormat.NONE:
        return None

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

            if INLINE_REPLY_PATTERN.match(content):
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
                    ReplyFormat.EMBED,
                    embed_color
                )

            return proxy_content
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
                'color': embed_color or 0x7289da,
                'description': (
                    f'{'✉️ ' if reference.get('attachments') else ''}'
                    f'**[Reply to:]({jump_url})** {content}'
                    if content.strip() else
                    f'*[click to see attachment{'' if len(reference.get('attachments', []))-1 else 's'}]({jump_url})*'
                    if reference.get('attachments') else
                    f'*[click to see message]({jump_url})*'
                )
            }

    return None


def do_roll(input: str) -> tuple[str, str, str, float]:
    for forbidden in {'ir', 'ie'}:
        if forbidden in input.split(':')[0]:
            raise ValueError(f'Forbidden command: {forbidden}')

    st = perf_counter()
    history, result = roll(input)
    et = perf_counter()
    return input, result, history, round((et-st)*1000, 4)


async def insert_blocks(
    content: str,
    debug_log: list[str]
) -> tuple[str, dict, bool]:
    roll_log = []

    rolls = []

    executor = ProcessPoolExecutor()

    for block in BLOCK_PATTERN.finditer(content):
        if CHANNEL_MENTION_PATTERN.match(block.group(1).strip()):
            continue  # ! do redirection

        if len(rolls) >= 10:
            if 'Max rolls reached' not in roll_log:
                roll_log.append('Max rolls reached')
            continue

        rolls.append((
            block.group(0),
            to_process(executor, do_roll, block.group(1))
        ))

    if not rolls:
        if roll_log:
            debug_log.append('\n  '.join(roll_log))
        executor.shutdown()
        return content, {}, True

    st = perf_counter()
    try:
        async with timeout(1):
            results = await gather(
                *(roll[1] for roll in rolls),
                return_exceptions=True)
    except TimeoutError:
        roll_log.append('Rolls timed out.')
        debug_log.append('\n  '.join(roll_log))
        executor.shutdown()
        return content, {}, True
    executor.shutdown()
    et = perf_counter()

    final_results = []

    for block, value in zip(
        (roll[0] for roll in rolls),  # noqa: F402
        results,
        strict=True
    ):
        if isinstance(value, BaseException):
            roll_log.append(f'Error on {block}:\n    {value}')
            continue

        input, result, history, time = value

        content = content.replace(
            block,
            f'`🎲{result}`',
            count=1
        )

        final_results.append((input, history, result, time))

    cx().set_attributes({
        'proxy.roll.times': [result[3] for result in final_results],
        'proxy.roll.total_time': round((et-st)*1000, 4)
    })

    def limit_string(input: str, limit: int) -> str:
        return input[:limit] + ('…' if len(input) > limit else '')

    fields = [(
        f'{limit_string(input, 94-len(result))}  ➜  {result}',
        limit_string(history, 105))
        for input, history, result, _ in final_results
    ]

    for field in fields:
        roll_log.append(f'{field[0]}\n    {field[1]}')

    if roll_log:
        debug_log.append('\n  '.join(
            ['Roll Log:', *roll_log]
        ))

    return (
        content,
        {'fields': [{
            'name': name,
            'value': value,
            'inline': False}
            for name, value in fields]}
        if final_results else {},
        False
    )


async def create_request(
    endpoint: str,
    token: str,
    json: dict,
    params: dict,
    files: list[File]
) -> CoroutineType[Any, Any, dict[str, Any] | str | None]:
    if not files:
        return request(
            Route(
                'POST',
                endpoint,
                token=token),
            json=json,
            params=params
        )

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


def filesize_check(
    size: int,
    limit: int,
    debug_log: list[str]
) -> bool:
    if size > limit:
        debug_log.append(
            f'Attachments exceed {round(limit / 1_048_576)} MB. '
            f'({round(size / 1_048_576, 2)} MB)')
        return False

    if size > 20_971_520:
        debug_log.append(
            'Only 20MB of attachments can be proxied at a time.')
        return False
    return True


async def _process_proxy(
    event: dict,
    start_time: int,
    emojis: list[ClonedEmoji]
) -> ProxyResult:
    publish_latency = True
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
            proxy.autoproxy.mode == AutoproxyMode.LATCH
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

    if not filesize_check(
        total_filesize,
        filesize_limit,
        debug_log
    ):
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    files = [
        File(
            data=BytesIO(data),
            filename=attachment['filename'],
            description=attachment.get('description'),
            spoiler=attachment['filename'].startswith('SPOILER_'),
            duration_secs=attachment.get('duration_secs'),
            waveform=attachment.get('waveform'),
            size=len(data))
        for attachment in event.get('attachments', [])
        if (data := await (
            await GENERAL_SESSION.get(attachment['url'])
        ).read())
    ]

    if not filesize_check(
        sum(file.size or 0 for file in files),
        filesize_limit,
        debug_log
    ):
        await save_debug_log(event, debug_log)
        return ProxyResult(False, emojis)

    with span(  # ? only start the span once we're proxying
        'proxying message',
        start_time=start_time,
        parent=proxy.traceparent,
        attributes={
            'proxy.autoproxy': (
                ('guild' if proxy.autoproxy.guild else 'global')
                if proxy.autoproxy else 'none'),
            'proxy.reason': proxy.reason,
            'proxy.cloned_emojis': 0,
            'proxy.attachment_size': total_filesize,
        }
    ):
        await redis.set(
            f'pending_proxy:{event['channel_id']}:{event['id']}',
            '1', ex=timedelta(seconds=30)
        )

        handlers = ({
            'userproxy': userproxy_handler,
            'webhook': webhook_handler
        } if (
            proxy.member.userproxy and
            int(event['guild_id']) in
            proxy.member.userproxy.guilds
        ) else {
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
                if name == 'webhook':
                    await save_debug_log(event, debug_log)
                    return ProxyResult(False, emojis)
                continue

            tasks = [
                request(
                    Route(
                        'DELETE',
                        '/channels/{channel_id}/messages/{message_id}',
                        token=env.bot_token,
                        channel_id=event['channel_id'],
                        message_id=event['id']),
                    reason='/plu/ral proxy')
                if not original_deleted else
                sleep(0),
                await create_request(
                    response.endpoint,
                    response.token,
                    response.json,
                    response.params,
                    files
                )
            ]

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
                        with suppress(BaseException):
                            await request(Route(
                                'POST',
                                f'/channels/{event["channel_id"]}/messages',
                                token=env.bot_token
                            ), json={
                                'embeds': [{
                                    'title': 'Proxy Failed',
                                    'description': 'Proxy deleted original message but failed to send proxy.',
                                    'color': 0xff6969,
                                    'fields': [{
                                        'name': 'Reason',
                                        'value': str(getattr(
                                            discord_responses[1],
                                            'detail',
                                            discord_responses[1]))[:1024],
                                        'inline': True}],
                                    'footer': {
                                        'text': 'Please report this in the support server, if possible.'}}]})
                        raise PluralExceptionCritical(
                            'Proxy deleted original message but failed to send proxy.'
                        ) from discord_responses[1]

                    debug_log.append(
                        'Userproxy bot failed to send message in this channel.')
                    await redis.delete(f'discord:member:{event['guild_id']}:{proxy.member.userproxy.bot_id}')
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
            user=(await Usergroup.get_by_user(int(event['author']['id']))).id,
            channel_id=int(event['channel_id']),
            member_id=proxy.member.id,
            reason=proxy.reason,
            webhook_id=message.get('webhook_id'),
            reference_id=event.get('referenced_message', {}).get('id')
        ).save()

        pipeline = redis.pipeline()

        latency = (
            ((int(message['id']) >> 22) + 1420070400000) -
            int(datetime.fromisoformat(
                event['edited_timestamp'] or event['timestamp']
            ).timestamp() * 1000)
        )

        cx().set_attributes({
            'proxy.latency': latency,
            'proxy.publish': publish_latency and not emojis
        })

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

        get_counter('proxies').add(
            1,
            {'type': name}
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
    debug_log: list[str],
    emojis: list[ClonedEmoji]
) -> ProxyResponse:
    channel = await Cache.get(
        f'discord:channel:{event['channel_id']}'
    )

    try:
        webhook = await get_webhook(
            event,
            channel.data.get('__plural_last_member') != proxy.last_member_string)
    except (NotFound, Forbidden):
        debug_log.append(
            'Bot does not have permission to create webhooks.')
        return ProxyResponse.failure(False)
    except OverWebhookLimit:
        debug_log.append(
            'Webhook limit (15) reached for this channel. /plu/ral requires 2 webhooks. Please contact a moderator.')
        return ProxyResponse.failure(False)

    if webhook.get('application_id', '1') is not None:
        # ? webhooks created by users don't need emojis cloned
        proxy.content = await insert_emojis(
            proxy.content,
            env.bot_token,
            emojis,
            debug_log
        )

        if len(proxy.content) > 2000:
            debug_log.append(
                'Message too long after emoji replacement.')
            return ProxyResponse.failure(False)

    embeds = []

    usergroup = await Usergroup.get_by_user(int(event['author']['id']))

    proxy.content, roll_embed, publish_latency = (
        await insert_blocks(proxy.content, debug_log)
    )

    if len(proxy.content) > 2000:
        debug_log.append(
            'Message too long after dice roll.')
        return ProxyResponse.failure(False)

    if event.get('referenced_message') is not None:
        reply = format_reply(
            proxy.content,
            event['referenced_message'] | {'guild_id': event['guild_id']},
            usergroup.config.reply_format,
            proxy.member.color
        )

        match reply:
            case str():
                proxy.content = reply
            case dict():
                embeds.append(reply)

    if roll_embed and usergroup.config.roll_embed:
        embeds.append(roll_embed)

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
            'username': proxy.member.get_display_name(
                usergroup,
                proxy.group,
                await Guild.get_by_id(int(event['guild_id']))),
            'avatar_url': proxy.avatar_url,
            'allowed_mentions': allowed_mentions(
                proxy,
                usergroup.config.ping_replies),
            'embeds': embeds},
        params=params,
        token=env.bot_token,
        publish_latency=publish_latency
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

        debug_log.append(
            'Userproxy member not found in cache. Fetching...'
        )

        try:
            member_data = await request(Route(
                'GET',
                '/guilds/{guild_id}/members/{user_id}',
                token=env.bot_token,
                guild_id=event['guild_id'],
                user_id=proxy.member.userproxy.bot_id))
        except NotFound:
            debug_log.append(
                'Userproxy member not found in server.')
            response = await GENERAL_SESSION.post(
                f'https://api.{env.domain}/members/{proxy.member.id}/userproxy/sync',
                headers=inject({
                    'Authorization': f'Bearer {env.cdn_upload_token}'}),
                json={
                    'author_id': int(event['author']['id']),
                    'patch_filter': ['guilds']})
            if response.status == 400:
                # ? userproxy bot token is likely invalid
                # ? manually ensure guild id is removed from list
                proxy.member.userproxy.guilds.discard(
                    int(event['guild_id']))
                await proxy.member.save()
            return ProxyResponse.failure(publish_latency)

        member = await Cache(
            member_data, [], False, 0
        ).save(
            f'discord:member:{event['guild_id']}:{proxy.member.userproxy.bot_id}',
            timedelta(minutes=10)
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
            debug_log,
            force_clone=True)
    except Unauthorized:
        debug_log.append(
            'Userproxy bot token is invalid or expired.')
        return ProxyResponse.failure(publish_latency)

    if len(proxy.content) > 2000:
        debug_log.append(
            'Message too long after emoji replacement.')
        return ProxyResponse.failure(False)

    proxy.content, roll_embed, block_publish_latency = (
        await insert_blocks(proxy.content, debug_log)
    )

    if len(proxy.content) > 2000:
        debug_log.append(
            'Message too long after dice roll.')
        return ProxyResponse.failure(False)

    publish_latency = publish_latency and block_publish_latency

    embeds = []

    usergroup = await Usergroup.get_by_user(int(event['author']['id']))

    if roll_embed and usergroup.config.roll_embed:
        embeds.append(roll_embed)

    return ProxyResponse(
        success=True,
        endpoint=f'/channels/{event['channel_id']}/messages',
        json={
            'content': proxy.content,
            'message_reference': {
                **event['message_reference'],
                'fail_if_not_exists': False
            } if event.get('message_reference') else None,
            'allowed_mentions': allowed_mentions(
                proxy,
                usergroup.config.ping_replies),
            'flags': (  # ? suppress only if suppress was not already there
                1 << 12  # ? suppress notifications
                & int(event.get('flags', 0)) ^
                1 << 12  # ? suppress notifications
            ) if event.get('mentions') else None,
            'embeds': embeds},
        params={},
        token=proxy.member.userproxy.token,
        publish_latency=publish_latency
    )


async def process_proxy(
    event: dict,
    start_time: int
) -> ProxyResult:
    emojis = []
    try:
        result = await _process_proxy(
            event,
            start_time,
            emojis
        )

        await delete_emojis(emojis)

        return result
    except BaseException as e:
        await delete_emojis(emojis)
        raise e
