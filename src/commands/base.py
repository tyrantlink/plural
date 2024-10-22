from __future__ import annotations
from discord import slash_command, ApplicationContext, Option, message_command, InteractionContextType, Message, InputTextStyle, Embed, Forbidden, MISSING
from src.converters import MemberConverter, GroupConverter, include_all_options
from src.views import DeleteConfirmation, ApiKeyView, HelpView
from src.helpers import CustomModal, send_error, send_success
from src.db import Group, Member, Message as DBMessage
import src.commands.autocomplete as autocomplete
from src.models import project, DebugMessage
from discord.ext.commands import Cog
from discord.ui import InputText
from typing import TYPE_CHECKING
from asyncio import gather

if TYPE_CHECKING:
    from discord.abc import MessageableChannel
    from src.client import Client


class BaseCommands(Cog):
    def __init__(self, client: Client):
        self.client = client

    @slash_command(name='ping', description='check the bot\'s latency')
    async def ping(self, ctx: ApplicationContext):
        await ctx.response.send_message(
            f'pong! {round(self.client.latency*1000)}ms',
            ephemeral=True
        )

    @slash_command(
        name='manage',
        description='manage your system',
        options=[
            Option(
                str,
                name='group',
                description='group to select from',
                default='default',
                autocomplete=autocomplete.groups),
            Option(
                str,
                name='member',
                description='member to manage',
                required=False,
                autocomplete=autocomplete.members)])
    async def slash_manage(self, ctx: ApplicationContext, group: str, member: str) -> None:
        await send_error(ctx, 'menu management has not been implemented yet')

    @message_command(
        name='/plu/ral edit',
        contexts={InteractionContextType.guild})
    async def message_plural_edit(self, ctx: ApplicationContext, message: Message):
        if ctx.guild is None:
            return  # ? never going to happen mypy is just stupid

        if message.webhook_id is None:
            await send_error(ctx, 'message is not a proxied message!')
            return

        webhook = await self.client.get_proxy_webhook(
            message.channel)

        if message.webhook_id != webhook.id:
            await send_error(ctx, 'message is not a proxied message!')
            return

        db_message = await self.client.db.message(
            proxy_id=message.id
        )

        if db_message is None:
            await send_error(ctx, 'message could not be found, is it too old?')
            return

        if ctx.author.id != db_message.author_id:
            await send_error(ctx, 'you can only edit your own messages!')
            return

        modal = CustomModal(
            title='edit message',
            children=[
                InputText(
                    label='edit message',
                    style=InputTextStyle.long,
                    min_length=1,
                    max_length=2000,
                    value=message.content,
                    placeholder='message content'
                )
            ]
        )

        await ctx.response.send_modal(modal)

        await modal.wait()

        new_content = modal.children[0].value

        if new_content == message.content:
            await send_error(modal.interaction, 'no changes were made')
            return

        await gather(
            modal.interaction.response.defer(),
            webhook.edit_message(
                message.id,
                content=new_content,
                thread=(
                    message.channel
                    if getattr(message.channel, 'parent', None) is not None else
                    MISSING
                )
            )
        )

    @slash_command(
        name='autoproxy',
        description='automatically proxy messages. leave empty to toggle',
        checks=[include_all_options],
        options=[
            Option(
                bool,
                name='enabled',
                description='enable or disable auto proxying',
                required=False
            ),
            Option(
                MemberConverter,
                name='member',
                description='set to a specific member immediately',
                required=False,
                autocomplete=autocomplete.members),
            Option(
                bool,
                name='server_only',
                description='whether to enable/disable in every server or just this one',
                default=True),
            Option(
                GroupConverter,
                name='group',
                description='group to restrict results to',
                required=False,
                autocomplete=autocomplete.groups)],
        contexts={InteractionContextType.guild})
    async def slash_autoproxy(
        self,
        ctx: ApplicationContext,
        enabled: bool | None,
        member: Member | None,
        server_only: bool,
        group: Group | None
    ) -> None:
        assert ctx.interaction.user is not None
        if ctx.guild is None and server_only:
            await send_error(ctx, 'you must use this command in a server when the `server_only` option is enabled')
            return

        latch = await self.client.db.latch(
            ctx.interaction.user.id,
            ctx.guild.id if server_only else 0,  # type: ignore #? mypy is stupid
            create=True
        )

        latch.enabled = bool(
            enabled
            if enabled is not None else
            member or not latch.enabled
        )

        if member is not None:
            latch.member = member.id

        if not latch.enabled:
            latch.member = None

        success_message = (
            # ? mypy is stupid
            f'autoproxying in `{ctx.guild.name}` is now '  # type: ignore
            if server_only else
            'global autoproxy is now '
        )

        success_message += 'enabled' if latch.enabled else 'disabled'

        if latch.enabled:
            success_message += f' and set to {
                f'member `{member.name}`'
                if member else
                'the next member to send a message'}'

        await gather(
            latch.save(),
            send_success(ctx, success_message)
        )

    @slash_command(
        name='switch',
        description='quickly switch global autoproxy',
        options=[
            Option(
                MemberConverter,
                name='member',
                description='member to switch to',
                required=True,
                autocomplete=autocomplete.members),
            Option(
                bool,
                name='enabled',
                description='enable or disable auto proxying',
                default=True)])
    async def slash_switch(self, ctx: ApplicationContext, member: Member, enabled: bool) -> None:
        await self.slash_autoproxy(ctx, enabled, member, False, None)

    @slash_command(
        name='delete_all_data',
        description='delete all your data')
    async def slash_delete_all_data(self, ctx: ApplicationContext) -> None:
        await ctx.response.send_message(
            embed=Embed(
                title='are you sure?',
                description='this will delete all your data, including groups, members, avatars, latches, and messages',
                color=0xff6969
            ),
            view=DeleteConfirmation(self.client),
            ephemeral=True
        )

    @slash_command(
        name='reproxy',
        description='reproxy your last message',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='member to reproxy as',
                autocomplete=autocomplete.members),
            Option(  # ? not used in command, kept for autocomplete
                GroupConverter,
                name='group',
                description='group to restrict results to',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_reproxy(self, ctx: ApplicationContext, member: Member, group: Group):
        if not isinstance(ctx.channel, MessageableChannel):
            await send_error(ctx, 'channel is not a messageable object')
            return  # ? mypy is stupid, this will never happen

        try:
            last_channel_messages = await ctx.channel.history(limit=1).flatten()

            if not isinstance(last_channel_messages, list):  # ? mypy is stupid
                await send_error(ctx, 'failed to fetch recent messages')
                return

        except Forbidden:
            await send_error(
                ctx,
                'failed to fetch recent messages, i do not have permission to read message history')
            return

        if len(last_channel_messages) == 0:
            await send_error(ctx, 'no messages found in this channel')
            return

        message = last_channel_messages[0]

        last_proxy_message = await DBMessage.find_one(
            {
                'author_id': ctx.author.id,
                'proxy_id': message.id
            },
            sort=[('ts', -1)]
        )

        if last_proxy_message is None:
            await send_error(
                ctx,
                'no messages found, you cannot reproxy a message that was not the most recent message, or a message older than 30 minutes')
            return

        webhook = await self.client.get_proxy_webhook(
            ctx.channel
        )

        if webhook is None:
            await send_error(ctx, 'could not find the proxy webhook')
            return

        avatar = None
        if member.avatar:
            image = await self.client.db.image(member.avatar, False)
            if image is not None:
                avatar = (
                    f'{project.base_url}/avatars/{image.id}.{image.extension}')

        app_emojis, proxy_content = await self.client.process_emotes(message.content)

        responses = await gather(
            message.delete(reason='/plu/ral reproxy'),
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
                embeds=message.embeds or MISSING,
                files=[
                    await attachment.to_file()
                    for attachment in message.attachments
                ]
            )
        )

        await self.client.db.new.message(
            original_id=message.id,
            proxy_id=responses[1].id,
            author_id=message.author.id
        ).save()

        for app_emoji in app_emojis:
            await app_emoji.delete()

        await send_success(ctx, 'message reproxied successfully')

    @message_command(
        name='/plu/ral debug')
    async def message_plural_debug(self, ctx: ApplicationContext, message: Message) -> None:
        if ctx.guild is None:
            await send_error(ctx, 'this command can only be used in a guild')
            return

        debug_log: list[DebugMessage | str] = [DebugMessage.ENABLER]

        await self.client.process_proxy(message, debug_log, ctx.app_permissions)

        debug_log.remove(DebugMessage.ENABLER)

        await ctx.response.send_message(
            embed=Embed(
                title='debug log',
                description=f'```{'\n'.join(debug_log)}```',
                color=(
                    0x69ff69
                    if DebugMessage.SUCCESS in debug_log else
                    0xff6969
                )
            ),
            ephemeral=True
        )

    @slash_command(
        name='api',
        description='get an or refresh api key')
    async def slash_api(self, ctx: ApplicationContext):
        if ctx.interaction.user is None:
            await send_error(ctx, 'you do not exist')
            return

        view = ApiKeyView(self.client)

        await ctx.response.send_message(
            embed=view.embed,
            view=view,
            ephemeral=True
        )

    @message_command(
        name='/plu/ral proxy info')
    async def message_plural_proxy_info(self, ctx: ApplicationContext, message: Message):
        if message.webhook_id is None:
            await send_error(ctx, 'message is not a proxied message!')
            return

        db_message = await self.client.db.message(
            proxy_id=message.id
        )

        if db_message is None:
            await send_error(ctx, 'message could not be found, it is either too old or not proxied by the bot')
            return

        embed = Embed(
            title='proxy info',
            color=0x69ff69
        )

        embed.add_field(
            name='author',
            value=f'<@{db_message.author_id}>',
            inline=False
        )

        embed.set_footer(
            text=(
                f'original message id: {db_message.original_id or 'sent through /plu/ral api'}'),
        )

        await ctx.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @slash_command(
        name='help',
        description='get started with the bot')
    async def slash_help(self, ctx: ApplicationContext):
        view = HelpView()
        await ctx.response.send_message(
            embed=view.embed,
            view=view,
            ephemeral=True
        )
