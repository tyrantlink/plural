from __future__ import annotations
from discord import slash_command, ApplicationContext, Option, message_command, InteractionContextType, Message, InputTextStyle, Embed, Forbidden, MISSING
from src.helpers import CustomModal, send_error, send_success
from src.db import Group, Member, Message as DBMessage
import src.commands.autocomplete as autocomplete

from src.views import DeleteConfirmation
from discord.ext.commands import Cog
from discord.ui import InputText
from typing import TYPE_CHECKING
from src.project import project
from asyncio import gather

if TYPE_CHECKING:
    from discord.abc import MessageableChannel
    from src.client import Client


class BaseCommands(Cog):
    def __init__(self, client: Client):
        self.client = client

    async def _base_group_getter(self, interaction: ApplicationContext, group: str) -> Group | None:
        resolved_group = await self.client.db.group_by_name(interaction.author.id, group)

        if resolved_group is None:
            if group == 'default':
                resolved_group = self.client.db.new.group('default')
                resolved_group.accounts.add(interaction.author.id)
                await resolved_group.save()
                return resolved_group

            await send_error(interaction, f'group `{group}` not found')
            return None

        return resolved_group

    async def _base_member_getter(
        self,
        interaction: ApplicationContext,
        group: str,
        member: str
    ) -> tuple[Group, Member] | tuple[None, None]:
        resolved_group = await self._base_group_getter(interaction, group)

        if resolved_group is None:
            return None, None

        resolved_member = await resolved_group.get_member_by_name(member)

        if resolved_member is None:
            await send_error(interaction, f'member `{member}` not found')
            return None, None

        return resolved_group, resolved_member

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
        name='plural edit',
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
        options=[
            Option(
                bool,
                name='enabled',
                description='enable or disable auto proxying',
                required=False
            ),
            Option(
                str,
                name='member',
                description='set to a specific member immediately',
                required=False,
                autocomplete=autocomplete.members),
            Option(
                str,
                name='group',
                description='group to select from',
                default='default',
                required=False,
                autocomplete=autocomplete.groups)],
        contexts={InteractionContextType.guild})
    async def slash_autoproxy(self, ctx: ApplicationContext, enabled: bool | None, member: str | None, group: str):
        if ctx.interaction.user is None:
            await send_error(ctx, 'you do not exist')
            return

        if ctx.guild is None:
            return

        resolved_group = await self.client.db.group_by_name(
            ctx.interaction.user.id,
            group
        )

        if resolved_group is None:
            await send_error(ctx, f'group `{group}` not found')
            return

        latch = await self.client.db.latch(
            ctx.interaction.user.id,
            ctx.guild.id,
            create=True
        )

        latch.enabled = bool(enabled or member or not latch.enabled)

        if member is not None:
            resolved_member = await resolved_group.get_member_by_name(member)

            if resolved_member is None:
                await send_error(ctx, f'member `{member}` not found in group `{group}`')
                return

            latch.member = resolved_member.id

        if not latch.enabled:
            latch.member = None

        success_message = f'autoproxying in `{ctx.guild.name}` is now {
            'enabled' if latch.enabled else 'disabled'}'

        if latch.enabled:
            success_message += f' and set to {
                f'member `{member}`'
                if member else
                'the next member to send a message'}'

        await gather(
            latch.save(),
            send_success(ctx, success_message)
        )

    @slash_command(
        name='delete_all_data',
        description='delete all your data')
    async def slash_delete_all_data(self, ctx: ApplicationContext):
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
        options=[
            Option(
                str,
                name='member',
                description='member to reproxy as',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='group',
                description='group to select from',
                default='default',
                autocomplete=autocomplete.groups)],)
    async def slash_reproxy(self, ctx: ApplicationContext, member: str, group: str):
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return

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
        if resolved_member.avatar:
            image = await self.client.db.image(resolved_member.avatar, False)
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
                username=resolved_member.name,
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
