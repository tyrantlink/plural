from __future__ import annotations
from discord import AutoShardedBot, AppEmoji, Webhook, TextChannel, VoiceChannel, StageChannel, ForumChannel, Message, Permissions, MISSING, AllowedMentions
from src.db import MongoDatabase, Member, Latch
from re import finditer, match, escape, Match
from src.models import project, DebugMessage
from src.helpers import format_reply
from typing import TYPE_CHECKING
from .emoji import ProbableEmoji
from time import perf_counter
from asyncio import gather


if TYPE_CHECKING:
    from discord.abc import MessageableChannel

GuildChannel = TextChannel | VoiceChannel | StageChannel | ForumChannel


class ClientBase(AutoShardedBot):
    def __init__(self, *args, **kwargs):
        self._st = perf_counter()
        self.db = MongoDatabase(project.mongo_uri)
        super().__init__(*args, **kwargs)

    async def process_emotes(self, message: str) -> tuple[set[AppEmoji], str]:
        guild_emojis = {
            ProbableEmoji(
                name=str(match.group(2)),
                id=int(match.group(3)),
                animated=match.group(1) is not None
            )
            for match in finditer(r'<(a)?:(\w{2,32}):(\d+)>', message)
        }

        app_emojis = {
            emoji.id: await self.create_emoji(
                name=emoji.name,
                image=await emoji.read(self.http),
            )
            for emoji in guild_emojis
        }

        for guild_emoji in guild_emojis:
            message = message.replace(
                str(guild_emoji), str(app_emojis.get(guild_emoji.id))
            )

        return set(app_emojis.values()), message

    async def get_proxy_webhook(self, channel: MessageableChannel) -> Webhook:
        resolved_channel = getattr(channel, 'parent', channel)

        if not isinstance(resolved_channel, GuildChannel):
            raise ValueError('resolved channel is not a guild channel')

        webhook = await self.db.webhook(resolved_channel.id)

        if webhook is not None:
            # ? temp migration
            if webhook.guild is None:
                webhook.guild = resolved_channel.guild.id
                await webhook.save_changes()

            return Webhook.from_url(
                webhook.url,
                session=self.http._HTTPClient__session  # type: ignore # ? use it anyway
            )

        for webhook in await resolved_channel.webhooks():
            if webhook.name == '/plu/ral proxy':
                await self.db.new.webhook(
                    resolved_channel.id,
                    resolved_channel.guild.id,
                    webhook.url
                ).save()
                return webhook

        webhook = await resolved_channel.create_webhook(
            name='/plu/ral proxy',
            reason='required for /plu/ral to function'
        )

        await self.db.new.webhook(
            resolved_channel.id,
            resolved_channel.guild.id,
            webhook.url
        ).save()

        return webhook

    def _ensure_proxy_preserves_mentions(self, check: Match) -> bool:
        for safety_match in finditer(
            r'<(?:(?:[@#]|:\S+|\/(?:\w+ ?){1,3}:)\d+|https?:\/\/[^\s]+)>',
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

    async def get_proxy_for_message(
        self,
        message: Message,
        debug_log: list[DebugMessage | str] | None = None
    ) -> tuple[Member, str, Latch | None] | tuple[None, None, None]:
        if debug_log is None:
            debug_log = []

        groups = await self.db.groups(message.author.id)

        channel_ids = {
            message.channel.id,
            getattr(message.channel, 'category_id', None),
            getattr(message.channel, 'parent_id', None)
        }
        channel_ids.discard(None)

        if message.guild is None:
            return None, None, None  # ? mypy stupid

        latch = await self.db.latch(message.author.id, message.guild.id)
        latch_return: None | tuple[Member, str, Latch] = None

        for group in groups.copy():
            if (  # ? this is a mess, if the system restricts channels and the message isn't in one of them, skip
                group.channels and
                not any(
                    channel_id in group.channels
                    for channel_id in channel_ids
                )
            ):
                if debug_log:
                    debug_log.append(
                        DebugMessage.GROUP_CHANNEL_RESTRICTED.format(group.name))
                continue

            for member_id in group.members.copy():
                member = await self.db.member(member_id)

                if member is None:
                    continue

                if latch and latch.enabled and latch.member == member.id:
                    # ? putting this here, if there are proxy tags given, prioritize them
                    # ? also having this check here ensures that channels are still checked
                    latch_return = member, message.content, latch

                for proxy_tag in member.proxy_tags:
                    if not proxy_tag.prefix and not proxy_tag.suffix:
                        continue

                    prefix, suffix = (
                        (escape(proxy_tag.prefix), escape(proxy_tag.suffix))
                        if not proxy_tag.regex else
                        (proxy_tag.prefix, proxy_tag.suffix)
                    )

                    check = match(
                        f'^({prefix})([\\s\\S]+)({suffix})$',
                        message.content
                    )

                    if check is not None:
                        if not self._ensure_proxy_preserves_mentions(check):
                            continue

                        if latch is not None and latch.enabled:
                            latch.member = member.id
                            await latch.save_changes()

                        return member, check.group(2), latch

        if latch is None:
            debug_log.append(DebugMessage.AUTHOR_NO_TAGS)

            return None, None, None

        if latch_return is not None:
            return latch_return

        if debug_log:
            debug_log.append(DebugMessage.AUTHOR_NO_TAGS_NO_LATCH)

        return None, None, None

    async def permission_check(
        self,
        message: Message,
        debug_log: list[DebugMessage | str] | None = None,
        channel_permissions: Permissions | None = None
    ) -> bool:
        if message.guild is None:
            return False

        # ? mypy stupid
        self_permissions = channel_permissions or message.channel.permissions_for(  # type: ignore
            message.guild.me)

        if not isinstance(self_permissions, Permissions):
            return False  # ? mypy stupid

        if self_permissions.send_messages is False:
            if debug_log:
                debug_log.append(DebugMessage.PERM_SEND_MESSAGES)

            return False

        if self_permissions.manage_webhooks is False:
            await message.channel.send(
                'i do not have the manage webhooks permission in this channel. please contact an admin',
                reference=message,
                mention_author=False
            )

            if debug_log:
                debug_log.append(DebugMessage.PERM_MANAGE_WEBHOOKS)

            return False

        if self_permissions.manage_messages is False:
            await message.channel.send(
                'i do not have the manage messages permission in this channel. please contact an admin',
                reference=message,
                mention_author=False
            )

            if debug_log:
                debug_log.append(DebugMessage.PERM_MANAGE_MESSAGES)

            return False

        return True

    async def process_proxy(
        self,
        message: Message,
        debug_log: list[DebugMessage | str] | None = None,
        channel_permissions: Permissions | None = None
    ) -> bool:
        if debug_log is None:
            # ? if debug_log is given by debug command, it will have DebugMessage.ENABLER, being a truthy value
            # ? if it's not given, we set it to an empty list here and never append to it
            debug_log = []

        if (
            message.author.bot or
            message.guild is None or
            not (message.content or message.attachments)
        ):
            if debug_log:
                if message.author.bot:
                    debug_log.append(DebugMessage.AUTHOR_BOT)

                if message.guild is None:
                    debug_log.append(DebugMessage.NOT_IN_GUILD)

                if not (message.content or message.attachments):
                    debug_log.append(DebugMessage.NO_CONTENT)

            return False

        member, proxy_content, latch = await self.get_proxy_for_message(message, debug_log)

        if member is None or proxy_content is None:
            return False

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

            return False

        if not await self.permission_check(message, debug_log, channel_permissions):
            return False

        if len(proxy_content) > 1980:
            await message.channel.send(
                'i cannot proxy message over 1980 characters',
                reference=message,
                mention_author=False,
                delete_after=10
            )

            if debug_log:
                debug_log.append(DebugMessage.OVER_TEXT_LIMIT)

            return False

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

            return False

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
            return False

        embed = MISSING
        if message.reference and isinstance(message.reference.resolved, Message):
            proxy_with_reply = format_reply(
                proxy_content, message.reference.resolved)

            if isinstance(proxy_with_reply, str):
                proxy_content = proxy_with_reply
            else:
                embed = proxy_with_reply

        avatar = None
        if member.avatar:
            image = await self.db.image(member.avatar, False)
            if image is not None:
                avatar = (
                    f'{project.base_url}/avatar/{image.id}.{image.extension}')

        if debug_log:
            debug_log.append(DebugMessage.SUCCESS)
            return True

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
                avatar_url=avatar,
                embed=embed,
                files=[
                    await attachment.to_file()
                    for attachment in message.attachments
                ],
                allowed_mentions=(
                    AllowedMentions(
                        users=(
                            [message.reference.resolved.author]
                            if message.reference.resolved.author in message.mentions else
                            []
                        )
                    )
                )
                if (
                    not embed == MISSING and
                    message.reference is not None and
                    isinstance(message.reference.resolved, Message)
                ) else
                MISSING
            )
        )

        await self.db.new.message(
            original_id=message.id,
            proxy_id=responses[1].id,
            author_id=message.author.id
        ).save()

        for app_emoji in app_emojis:
            await app_emoji.delete()

        return True

    async def handle_ping_reply(self, message: Message) -> None:
        #! discord does put webhook ids in message.mentions,
        #! so i can't tell if the reply is a ping or not,
        #! disabling this for now

        return

        if (
            message.reference is None or
            not isinstance(message.reference.resolved, Message) or
            message.reference.resolved.webhook_id is None
        ):
            return

        message_data = await self.db.message(proxy_id=message.reference.resolved.id)

        if message_data is None:
            return

        if message_data.author_id == message.author.id:
            return

        await message.channel.send(
            f'<@{message_data.author_id}>',
            reference=message,
            mention_author=False,
            delete_after=0
        )
