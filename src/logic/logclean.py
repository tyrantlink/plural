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

    def as_query(self) -> dict[str, str | int]:
        return {
            key: value
            for key, value in self.__dict__.items()
            if value is not None
        } or {
            'id': 0
        }  # ? never return an empty query


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
        dyno
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
        len(event.embeds) == 0 or
        event.embeds[0].footer is None or
        event.embeds[0].color != 16729871 or
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
