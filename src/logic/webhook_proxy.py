from src.discord.models import Emoji, MessageCreateEvent, Permission
from src.discord.http import get_from_cdn
from src.models import DebugMessage
from dataclasses import dataclass
from regex import finditer, Match
from asyncio import gather
from random import randint
from io import BytesIO


_emoji_index = randint(0, 999)


def emoji_index() -> str:
    global _emoji_index
    if _emoji_index == 999:
        _emoji_index = -1
    _emoji_index += 1
    return f'{_emoji_index:03}'


@dataclass(frozen=True)
class ProbableEmoji:
    name: str
    id: int
    animated: bool

    def __str__(self) -> str:
        return f'<{"a" if self.animated else ""}:{self.name}:{self.id}>'

    async def read(self) -> bytes:
        return await get_from_cdn(
            f'https://cdn.discordapp.com/emojis/{self.id}.{"gif" if self.animated else "png"}')


async def process_emoji(message: str) -> tuple[list[Emoji], str]:
    guild_emojis = {
        ProbableEmoji(
            name=str(match.group(2)),
            id=int(match.group(3)),
            animated=match.group(1) is not None
        )
        for match in finditer(r'<(a)?:(\w{2,32}):(\d+)>', message)
    }

    app_emojis = {}

    async def _create_emoji(emoji: ProbableEmoji) -> None:
        app_emojis.update({
            emoji.id: await Emoji.create_application_emoji(
                name=f'{emoji.name[:28]}_{emoji_index()}',
                image=await emoji.read(),
            )
        })

    await gather(*[_create_emoji(emoji) for emoji in guild_emojis])

    for guild_emoji in guild_emojis:
        message = message.replace(
            str(guild_emoji), str(app_emojis.get(guild_emoji.id))
        )

    return list(app_emojis.values()), message


def _ensure_proxy_preserves_mentions(check: Match) -> bool:
    for safety_match in finditer(
        r'<(?:(?:[@#]|sound:|:\S+|\/(?:\w+ ?){1,3}:)\d+|https?:\/\/[^\s]+)>',
        check.string
    ):
        if (
            (
                # ? if the prefix is present
                check.end(1) and
                safety_match.start() < check.end(1)
            ) or
            (
                # ? if the suffix is present
                (check.start(3)-len(check.string)) and
                safety_match.end() > check.start(3)
            )
        ):
            return False

    return True


async def process_proxy(
    message: MessageCreateEvent,
    debug_log: list[DebugMessage | str] | None = None,
    channel_permissions: Permission | None = None
) -> tuple[bool, list[Emoji] | None]:
    assert message.author is not None
    if debug_log is None:
        # ? if debug_log is given by debug command, it will have DebugMessage.ENABLER, being a truthy value
        # ? if it's not given, we set it to an empty list here and never append to it
        debug_log = []

    valid_content = bool(
        message.content or message.attachments or message.stickers or message.poll)

    if (
        message.author.bot or
        message.guild is None or
        not valid_content or
        (message.attachments and message.stickers)
    ):
        if debug_log:
            if message.author.bot:
                debug_log.append(DebugMessage.AUTHOR_BOT)

            if message.guild is None:
                debug_log.append(DebugMessage.NOT_IN_GUILD)

            if not valid_content:
                debug_log.append(DebugMessage.NO_CONTENT)

            if message.attachments and message.stickers:
                debug_log.append(DebugMessage.ATTACHMENTS_AND_STICKERS)

        return False, None

    member, proxy_content, latch = await get_proxy_for_message(message, debug_log)

    if member is None or proxy_content is None:
        return False, None

    if (
        latch is not None and
        latch.enabled and
        message.content.startswith('\\')
    ):
        # ? if latch is enabled and,
        # ? if message starts with single backslash, skip proxying this message,
        # ? if message starts with double backslash, reset member on latch
        if message.content.startswith('\\\\'):
            latch.member = None
            await latch.save_changes()

        if debug_log:
            debug_log.append(DebugMessage.AUTOPROXY_BYPASSED)

        return False, None

    if not await self.permission_check(message, debug_log, channel_permissions):
        return False, None

    if len(proxy_content) > 1980:
        await message.channel.send(
            'i cannot proxy message over 1980 characters',
            reference=message,
            mention_author=False,
            delete_after=10
        )

        if debug_log:
            debug_log.append(DebugMessage.OVER_TEXT_LIMIT)

        return False, None

    if sum(
        attachment.size
        for attachment in
        message.attachments
    ) > message.guild.filesize_limit:
        await message.channel.send(
            'attachments are above the file size limit',
            reference=message,
            mention_author=False,
            delete_after=10
        )

        if debug_log:
            debug_log.append(DebugMessage.OVER_FILE_LIMIT)

        return False, None

    webhook = await self.get_proxy_webhook(message.channel)

    # ? don't actually clone emotes if we're debugging
    app_emojis = set()
    if not debug_log:
        app_emojis, proxy_content = await self.process_emotes(proxy_content)

    if len(proxy_content) > 2000:
        await message.channel.send(
            'this message was over 2000 characters after processing emotes. proxy failed',
            reference=message,
            mention_author=False,
            delete_after=10
        )
        return False, app_emojis

    embed = MISSING
    if message.reference and isinstance(message.reference.resolved, Message):
        proxy_with_reply = format_reply(
            proxy_content, message.reference.resolved)

        if isinstance(proxy_with_reply, str):
            proxy_content = proxy_with_reply
        else:
            embed = proxy_with_reply

    if debug_log:
        debug_log.append(DebugMessage.SUCCESS)
        return True, app_emojis

    attachments = [
        await attachment.to_file()
        for attachment in message.attachments
    ]
    if message.stickers and not attachments:
        if any(
            sticker.format.name == 'lottie'
            for sticker in message.stickers
        ):
            if debug_log:
                debug_log.append(DebugMessage.INCOMPATIBLE_STICKERS)
            return False, app_emojis

        attachments = [
            File(
                BytesIO(await sticker.read(self.http)),
                filename=sticker.filename
            )
            for _sticker in message.stickers
            if (sticker := ProbableSticker(
                name=_sticker.name,
                id=_sticker.id,
                format=_sticker.format
            )).format.name != 'lottie'
        ]

    if (
        message.poll and
        message.poll.duration is None and
        isinstance(message.poll.expiry, datetime)
    ):
        message.poll.duration = round((
            message.poll.expiry - message.created_at
        ).total_seconds() / 60 / 60)

    responses = await gather(
        message.delete(reason='/plu/ral proxy'),
        webhook.send(
            content=proxy_content,
            thread=(
                message.channel
                if getattr(message.channel, 'parent', None) is not None else
                MISSING
            ),
            wait=True,
            username=f'{member.name} {((await member.get_group()).tag or '')}',
            avatar_url=await member.get_avatar_url(),
            embed=embed,
            files=attachments,
            allowed_mentions=(
                AllowedMentions(
                    users=(
                        [message.reference.resolved.author]
                        if message.reference.resolved.author in message.mentions else
                        []
                    )
                )
            ) if (
                not embed == MISSING and
                message.reference is not None and
                isinstance(message.reference.resolved, Message)
            ) else MISSING,
            poll=message.poll or MISSING
        )
    )

    await self.db.new.message(
        original_id=message.id,
        proxy_id=responses[1].id,
        author_id=message.author.id
    ).save()

    return True, app_emojis
