from src.discord.listeners import listen, ListenerType
from src.discord import MessageCreateEvent
from dataclasses import dataclass
from src.db import Log, Config
from regex import search


@dataclass
class LogExtract:
    author_id: int | None = None
    message_id: int | None = None
    author_name: str | None = None
    channel_id: int | None = None
    content: str | None = None

    def as_full_query(self) -> dict[str, str | int]:
        return {
            key: value
            for key, value in self.__dict__.items()
            if value is not None
        } or {
            'id': 0
        }  # ? never return an empty query

    def as_query(self) -> dict[str, str | int]:
        return (
            self.as_full_query()
            if self.message_id is None
            else {
                'message_id': self.message_id
            }
        )


@listen(ListenerType.MESSAGE_CREATE)
async def on_message_create(event: MessageCreateEvent):
    if (
        event.author is None or
        not event.author.bot or
        event.guild_id is None
    ):
        return

    config = await Config.get(event.guild_id)

    if config is None or not config.logclean:
        return

    for matcher in [
        dyno,
        carlbot,
        probot,
        catalogger,
    ]:
        extract = matcher(event)
        if extract is None:
            continue

        if not await Log.find_one(extract.as_query()):
            continue

        await event.delete('/plu/ral log clean')


def dyno(event: MessageCreateEvent) -> LogExtract | None:
    assert event.author is not None

    if event.webhook_id is None:
        return None

    if (
        event.embeds is None or
        len(event.embeds) != 1 or
        event.embeds[0].footer is None or
        event.embeds[0].author is None or
        event.embeds[0].description is None
    ):
        return None

    match = search(
        r'Author: (?P<author>\d+) \| Message ID: (?P<message>\d+)',
        event.embeds[0].footer.text,
    )

    if match is None:
        return None

    extract = LogExtract(
        author_name=event.embeds[0].author.name,
        author_id=int(match.group('author')),
        message_id=int(match.group('message')),
    )

    match = search(
        r'\*\*Message sent by <@(?P<author>\d+)> Deleted in <#(?P<channel>\d+)>\*\*(?:\n(?P<content>[\s\S]+))?',
        event.embeds[0].description,
    )

    if match is None:
        return None

    if extract.author_id != int(match.group('author')):
        return None

    extract.channel_id = int(match.group('channel'))
    extract.content = match.group('content')

    return extract


def carlbot(event: MessageCreateEvent) -> LogExtract | None:
    assert event.author is not None

    if (
        event.embeds is None or
        len(event.embeds) != 1 or
        event.embeds[0].footer is None or
        event.embeds[0].author is None or
        event.embeds[0].description is None
    ):
        return None

    match = search(
        r'(?P<content>[\s\S]+)\n\nMessage ID: (?P<message>\d+)',
        event.embeds[0].description,
    )

    if match is None:
        return None

    extract = LogExtract(
        author_name=event.embeds[0].author.name,
        content=match.group('content'),
        message_id=int(match.group('message')),
    )

    match = search(
        r'ID: (?P<author>\d+)',
        event.embeds[0].footer.text,
    )

    if match is None:
        return None

    extract.author_id = int(match.group('author'))

    return extract


def probot(event: MessageCreateEvent) -> LogExtract | None:
    assert event.author is not None

    if (
        event.embeds is None or
        len(event.embeds) != 1 or
        event.embeds[0].author is None or
        event.embeds[0].description is None
    ):
        return None

    match = search(
        r':wastebasket: \*\*Message sent by <@(?P<author>\d+)> deleted in <#(?P<channel>\d+)>.\*\*\n(?P<content>[\s\S]+)',
        event.embeds[0].description,
    )

    if match is None:
        return None

    return LogExtract(
        author_id=int(match.group('author')),
        channel_id=int(match.group('channel')),
        content=match.group('content'),
    )


def catalogger(event: MessageCreateEvent) -> LogExtract | None:
    assert event.author is not None

    if (
        event.embeds is None or
        len(event.embeds) != 1 or
        event.embeds[0].footer is None or
        event.embeds[0].author is None or
        event.embeds[0].description is None or
        event.embeds[0].fields is None or
        len(event.embeds[0].fields) != 2 or
        event.embeds[0].title is None or
        event.embeds[0].title != 'Message deleted'
    ):
        return None

    match = search(
        r'<#(?P<channel1>\d+)>\nID: (?P<channel2>\d+)',
        event.embeds[0].fields[0].value
    )

    if match is None or match.group('channel1') != match.group('channel2'):
        return None

    extract = LogExtract(
        author_name=event.embeds[0].author.name,
        channel_id=int(match.group('channel1'))
    )

    match = search(
        r'<@(?P<author1>\d+)>\n(?P<author_name>.{2,32})\nID: (?P<author2>\d+)',
        event.embeds[0].fields[1].value
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
        event.embeds[0].footer.text
    )

    if match is None:
        return None

    extract.message_id = int(match.group('message'))

    match = search(
        r'(?P<content>[\s\S]+)',
        event.embeds[0].description
    )

    if match is None:
        return None

    extract.content = match.group('content')

    return extract
