from __future__ import annotations
from discord import AutoShardedBot, AppEmoji, Webhook, TextChannel, VoiceChannel, StageChannel, Message, Permissions, MISSING, AllowedMentions
from re import finditer, match, escape, Match
from src.db import MongoDatabase, Member
from src.helpers import format_reply
from typing import TYPE_CHECKING
from .emoji import ProbableEmoji
from src.project import project
from .embeds import ReplyEmbed
from time import perf_counter
from asyncio import gather


if TYPE_CHECKING:
    from discord.abc import MessageableChannel

GuildChannel = TextChannel | VoiceChannel | StageChannel


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
            return Webhook.from_url(
                webhook.url,
                session=self.http._HTTPClient__session  # type: ignore # ? use it anyway
            )

        for webhook in await resolved_channel.webhooks():
            if webhook.name == '/plu/ral proxy':
                await self.db.new.webhook(
                    resolved_channel.id,
                    webhook.url
                ).save()
                return webhook

        webhook = await resolved_channel.create_webhook(
            name='/plu/ral proxy',
            reason='required for /plu/ral to function'
        )

        await self.db.new.webhook(
            resolved_channel.id,
            webhook.url
        ).save()

        return webhook

    def _ensure_proxy_preserves_mentions(self, check: Match) -> bool:
        for safety_match in finditer(
            f'<(?:[@#]|:\\S+:)\\d+>',
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

    async def get_proxy_for_message(self, message: Message) -> tuple[Member, str] | tuple[None, None]:
        groups = await self.db.groups(message.author.id)

        channel_ids = {
            message.channel.id,
            getattr(message.channel, 'category_id', None),
            getattr(message.channel, 'parent_id', None)
        }
        channel_ids.discard(None)

        if message.guild is None:
            return None, None  # ? mypy stupid

        latch = await self.db.latch(message.author.id, message.guild.id)

        for group in groups.copy():
            if (  # ? this is a mess, if the system restricts channels and the message isn't in one of them, skip
                group.channels and
                not any(
                    channel_id in group.channels
                    for channel_id in channel_ids
                )
            ):
                continue

            for member_id in group.members.copy():
                member = await self.db.member(member_id)

                if member is None:
                    continue

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

                        return member, check.group(2)

        if latch is None:
            return None, None

        if latch.enabled and latch.member is not None:
            member = await self.db.member(latch.member)

            if member is not None:
                return member, message.content

        return None, None

    async def permission_check(self, message: Message) -> bool:
        if message.guild is None:
            return False

        # ? mypy stupid
        self_permissions = message.channel.permissions_for(  # type: ignore
            message.guild.me)

        if not isinstance(self_permissions, Permissions):
            return False  # ? mypy stupid

        if self_permissions.send_messages is False:
            return False

        if self_permissions.manage_webhooks is False:
            await message.channel.send(
                'i do not have the manage webhooks permission in this channel. please contact an admin',
                reference=message,
                mention_author=False
            )
            return False

        if self_permissions.manage_messages is False:
            await message.channel.send(
                'i do not have the manage messages permission in this channel. please contact an admin',
                reference=message,
                mention_author=False
            )
            return False

        return True

    async def process_proxy(self, message: Message) -> bool:
        if (
            message.author.bot or
            message.guild is None or
            not (message.content or message.attachments)
        ):
            return False

        if message.content.startswith('\\'):
            if not message.content.startswith('\\\\'):
                return False

            latch = await self.db.latch(
                message.author.id,
                message.guild.id
            )

            if latch is not None:
                latch.member = None
                await latch.save_changes()

            return False

        member, proxy_content = await self.get_proxy_for_message(message)

        if member is None or proxy_content is None:
            return False

        if not await self.permission_check(message):
            return False

        if len(proxy_content) > 1980:
            await message.channel.send(
                'i cannot proxy message over 1980 characters',
                reference=message,
                mention_author=False,
                delete_after=10
            )
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
            return False

        webhook = await self.get_proxy_webhook(message.channel)

        app_emojis, proxy_content = await self.process_emotes(proxy_content)

        if len(proxy_content) > 2000:
            await message.channel.send(
                'this message was over 2000 characters after processing emotes. proxy failed',
                reference=message,
                mention_author=False,
                delete_after=10
            )
            return False

        proxy_with_reply = format_reply(proxy_content, message.reference)

        reply_with_embed = len(proxy_with_reply) > 2000

        if not reply_with_embed:
            proxy_content = proxy_with_reply

        avatar = None
        if member.avatar:
            image = await self.db.image(member.avatar, False)
            if image is not None:
                avatar = (
                    f'{project.base_url}/avatars/{image.id}.{image.extension}')

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
                username=member.name,
                avatar_url=avatar,
                embed=(
                    ReplyEmbed(
                        message.reference.resolved,
                        color=0x69ff69)
                    if (
                        reply_with_embed and
                        message.reference and
                        isinstance(message.reference.resolved, Message)
                    ) else
                    MISSING
                ),
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
                    not reply_with_embed and
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
