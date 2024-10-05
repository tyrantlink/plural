from __future__ import annotations
from discord import slash_command, ApplicationContext, Option, message_command, InteractionContextType, Message, InputTextStyle, Embed
from src.helpers import CustomModal, send_error, send_success
import src.commands.autocomplete as autocomplete
from src.views import DeleteConfirmation
from discord.ext.commands import Cog
from discord.ui import InputText
from typing import TYPE_CHECKING
from src.db import Group, Member
from asyncio import gather


if TYPE_CHECKING:
    from src.client.base import ClientBase


class BaseCommands(Cog):
    def __init__(self, client: ClientBase):
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
            message.channel)  # type: ignore

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

        await webhook.edit_message(
            message.id,
            content=new_content
        )

        await modal.interaction.response.defer()

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
                name='group',
                description='group to select from',
                default='default',
                required=False,
                autocomplete=autocomplete.groups),
            Option(
                str,
                name='member',
                description='set to a specific member immediately',
                required=False,
                autocomplete=autocomplete.members)],
        contexts={InteractionContextType.guild})
    async def slash_autoproxy(self, ctx: ApplicationContext, enabled: bool | None, group: str, member: str | None):
        if ctx.interaction.user is None:
            await send_error(ctx, 'you do not exist')
            return

        if ctx.guild_id is None:
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
            ctx.guild_id,
            create=True
        )

        latch.enabled = enabled if enabled is not None else not latch.enabled

        if member is not None:
            resolved_member = await resolved_group.get_member_by_name(member)

            if resolved_member is None:
                await send_error(ctx, f'member `{member}` not found in group `{group}`')
                return

            latch.member = resolved_member.id

        if not latch.enabled:
            latch.member = None

        success_message = f'autoproxying in {ctx.guild.name} is now {
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
