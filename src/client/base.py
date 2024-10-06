from discord import AutoShardedBot, AppEmoji, Webhook, TextChannel, VoiceChannel, StageChannel, Message, Permissions
from src.db import MongoDatabase, Member
from re import finditer, match, escape
from src.commands import Commands
from .emoji import ProbableEmoji
from src.project import project
from time import perf_counter

GuildChannel = TextChannel | VoiceChannel | StageChannel


class ClientBase(AutoShardedBot):
    def __init__(self, *args, **kwargs):
        self._st = perf_counter()
        self.db = MongoDatabase(project.mongo_uri)
        super().__init__(*args, **kwargs)

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        self.add_cog(Commands(self))
        await self.db.connect()
        await self.login(token)
        await self.connect(reconnect=reconnect)

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

    async def get_proxy_webhook(self, channel: GuildChannel) -> Webhook:
        resolved_channel: GuildChannel = getattr(channel, 'parent', channel)

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

                    check = match(
                        (
                            f'^{proxy_tag.prefix}(.+){proxy_tag.suffix}$'
                            if proxy_tag.regex else
                            (
                                f'^{escape(proxy_tag.prefix)}(.+){escape(proxy_tag.suffix)}$')
                        ),
                        message.content
                    )
                    if check is not None:
                        if latch is not None and latch.enabled:
                            latch.member = member.id
                            await latch.save_changes()

                        return member, check.group(1)

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
