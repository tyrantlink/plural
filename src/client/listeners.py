from discord import ApplicationContext, DiscordException, Message, RawReactionActionEvent
from src.helpers import send_error
from time import perf_counter
from .base import ClientBase


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
        if await self.process_proxy(message):
            return

        await self.handle_ping_reply(message)

    async def on_message_edit(self, before: Message, after: Message) -> None:
        if before.content == after.content:
            return None

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

    async def on_application_command_error(self, ctx: ApplicationContext, exception: DiscordException) -> None:
        error = str(exception).removeprefix(
            'Application Command raised an exception: ')

        if error.startswith('DBConversionError: '):
            await send_error(ctx, error.removeprefix('DBConversionError: '))
            return

        await send_error(ctx, error)

        raise exception
