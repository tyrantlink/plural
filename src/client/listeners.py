from discord import Message, MISSING, RawReactionActionEvent
from src.project import project
from .embeds import ReplyEmbed
from time import perf_counter
from .base import ClientBase
from asyncio import gather


class ClientListeners(ClientBase):
    def __init__(self, *args, **kwargs):
        self._st = perf_counter()
        super().__init__(*args, **kwargs)

    async def on_connect(self) -> None:
        await self.sync_commands()

        shards = (
            (
                f' with {self.shard_count} shard{"s" if self.shard_count != 1 else ""}')
            if self.shard_count is not None else
            ''
        )

        if self.user is None:
            # ? this doesn't happen mypy is just stupid
            raise ValueError(
                'on_connect called while not connected to discord')

        print(
            f'{self.user.name} connected to discord in {round(perf_counter()-self._st, 2)} seconds{shards}')

    async def on_message(self, message: Message) -> None:
        if (
            message.author.bot or
            message.guild is None or
            not (message.content or message.attachments)
        ):
            return

        if message.content.startswith('\\'):
            if not message.content.startswith('\\\\'):
                return

            latch = await self.db.latch(
                message.author.id,
                message.guild.id
            )

            if latch is not None:
                latch.member = None
                await latch.save_changes()

            return

        member, proxy_content = await self.get_proxy_for_message(message)

        if member is None or proxy_content is None:
            return

        if not await self.permission_check(message):
            return

        if len(proxy_content) > 2000:
            await message.channel.send(
                'i cannot proxy message over 2000 characters',
                reference=message,
                mention_author=False,
                delete_after=10
            )
            return

        # ? it's never going to be outside of a guild
        webhook = await self.get_proxy_webhook(
            message.channel  # type: ignore
        )

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
            return

        app_emojis, proxy_content = await self.process_emotes(proxy_content)

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
                        color=member.color or 0x69ff69)
                    if (
                        message.reference and
                        isinstance(message.reference.resolved, Message)
                    ) else
                    MISSING
                ),
                files=[
                    await attachment.to_file()
                    for attachment in message.attachments
                ]
            )
        )

        await self.db.new.message(
            original_id=message.id,
            proxy_id=responses[1].id,
            author_id=message.author.id
        ).save()

        for app_emoji in app_emojis:
            await app_emoji.delete()

    async def on_message_edit(self, before: Message, after: Message) -> None:
        if await after.channel.history(limit=1).flatten() != [after]:
            return None

        await self.on_message(after)

    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        if (
            payload.user_id == self.user.id or  # type: ignore
            payload.guild_id is None or
            payload.member is None or
            payload.member.bot or
            payload.emoji.name not in {'❌'}
        ):
            return

        match payload.emoji.name:  # ? i might add more later
            case '❌':
                message = await self.db.message(
                    proxy_id=payload.message_id
                )

                if message is None:
                    return

                if payload.user_id != message.author_id:
                    return

                channel = payload.member.guild.get_channel_or_thread(
                    payload.channel_id
                )

                if channel is None:
                    return

                webhook = await self.get_proxy_webhook(
                    channel  # type: ignore
                )

                await webhook.delete_message(
                    payload.message_id,
                    thread_id=(
                        payload.channel_id
                        if getattr(channel, 'parent', None) is not None else
                        None
                    )
                )
