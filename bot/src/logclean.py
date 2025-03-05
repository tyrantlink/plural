from dataclasses import dataclass
from hashlib import sha256

from regex import search

from plural.db import Guild, ProxyLog
from plural.otel import span

from src.http import request, Route
from src.models import env


@dataclass
class LogExtract:
    author_id: int | None = None
    message_id: int | None = None
    author_name: str | None = None
    channel_id: int | None = None
    content: str | None = None

    def as_full_query(self) -> dict[str, str | int]:
        return {
            key: (
                sha256(str(value).encode()).hexdigest()
                if key == 'content'
                else value)
            for key, value in self.__dict__.items()
            if value is not None
        }

    def as_query(self) -> dict[str, str | int]:
        return (
            self.as_full_query()
            if self.message_id is None
            else {
                'message_id': self.message_id
            }
        )


async def logclean(event: dict, start_time: int) -> None:
    if (
        event.get('author') is None or
        not event['author'].get('bot') or
        event.get('guild_id') is None
    ):
        return

    guild = await Guild.get(int(event['guild_id']))

    if guild is None or not guild.config.logclean:
        return

    for matcher in [
        dyno,
        carlbot,
        probot,
        catalogger
    ]:
        if (extract := matcher(event)) is None:
            continue

        if not (query := extract.as_query()):
            continue

        if await ProxyLog.find_one(query):
            break
    else:
        return

    with span(
        f'logclean ({matcher.__name__})',
        start_time=start_time,
        attributes={
            'matcher': matcher.__name__,
        }
    ):
        await request(Route(
            'DELETE',
            '/channels/{channel_id}/messages/{message_id}',
            token=env.bot_token,
            channel_id=event['channel_id'],
            message_id=event['id']
        ))


def dyno(event: dict) -> LogExtract | None:
    if (
        event.get('webhook_id') is None or
        event.get('embeds') is None or
        len(event['embeds']) != 1 or
        event['embeds'][0].get('footer') is None or
        event['embeds'][0].get('author') is None or
        event['embeds'][0].get('description') is None
    ):
        return None

    match = search(
        r'Author: (?P<author>\d+) \| Message ID: (?P<message>\d+)',
        event['embeds'][0]['footer']['text']
    )

    if match is None:
        return None

    extract = LogExtract(
        author_name=event['embeds'][0]['author']['name'],
        author_id=int(match.group('author')),
        message_id=int(match.group('message')),
    )

    match = search(
        r'\*\*(?:Message|Image) sent by <@(?P<author>\d+)> Deleted in <#(?P<channel>\d+)>\*\*(?:\n(?P<content>[\s\S]+))?',
        event['embeds'][0]['description'],
    )

    if match is None:
        return None

    if extract.author_id != int(match.group('author')):
        return None

    extract.channel_id = int(match.group('channel'))
    extract.content = match.group('content')

    return extract


def carlbot(event: dict) -> LogExtract | None:
    if (
        event.get('embeds') is None or
        len(event['embeds']) != 1 or
        event['embeds'][0].get('footer') is None or
        event['embeds'][0].get('author') is None or
        event['embeds'][0].get('description') is None
    ):
        return None

    match = search(
        r'(?:(?P<content>[\s\S]+)\n\n)?Message ID: (?P<message>\d+)',
        event['embeds'][0]['description']
    )

    if match is None:
        return None

    extract = LogExtract(
        author_name=event['embeds'][0]['author']['name'],
        content=match.group('content'),
        message_id=int(match.group('message'))
    )

    match = search(
        r'ID: (?P<author>\d+)',
        event['embeds'][0]['footer']['text']
    )

    if match is None:
        return None

    extract.author_id = int(match.group('author'))

    return extract


def probot(event: dict) -> LogExtract | None:
    if (
        event.get('embeds') is None or
        len(event['embeds']) != 1 or
        event['embeds'][0].get('author') is None or
        event['embeds'][0].get('description') is None
    ):
        return None

    match = search(
        r':wastebasket: \*\*Message sent by <@(?P<author>\d+)> deleted in <#(?P<channel>\d+)>.\*\*\n(?P<content>[\s\S]+)',
        event['embeds'][0]['description']
    )

    if match is None:
        return None

    return LogExtract(
        author_id=int(match.group('author')),
        channel_id=int(match.group('channel')),
        content=match.group('content')
    )


def catalogger(event: dict) -> LogExtract | None:
    if (
        event.get('embeds') is None or
        len(event['embeds']) != 1 or
        event['embeds'][0].get('footer') is None or
        event['embeds'][0].get('author') is None or
        event['embeds'][0].get('description') is None or
        event['embeds'][0].get('fields') is None or
        len(event['embeds'][0]['fields']) not in {2, 3} or
        event['embeds'][0].get('title') is None or
        event['embeds'][0]['title'] != 'Message deleted'
    ):
        return None

    match = search(
        r'<#(?P<channel1>\d+)>\nID: (?P<channel2>\d+)',
        event['embeds'][0]['fields'][0]['value']
    )

    if (
        match is None or
        match.group('channel1') != match.group('channel2')
    ):
        return None

    extract = LogExtract(
        author_name=event['embeds'][0]['author']['name'],
        channel_id=int(match.group('channel1'))
    )

    match = search(
        r'<@(?P<author1>\d+)>\n(?P<author_name>.{2,32})\nID: (?P<author2>\d+)',
        event['embeds'][0]['fields'][1]['value']
    )

    if (
        match is None or
        match.group('author1') != match.group('author2') or
        extract.author_name != match.group('author_name')
    ):
        return None

    extract.author_id = int(match.group('author1'))

    match = search(
        r'ID: (?P<message>\d+)',
        event['embeds'][0]['footer']['text']
    )

    if match is None:
        return None

    extract.message_id = int(match.group('message'))

    match = search(
        r'(?P<content>[\s\S]+)|None',
        event['embeds'][0]['description']
    )

    if match is None:
        return None

    extract.content = match.group('content')

    return extract
