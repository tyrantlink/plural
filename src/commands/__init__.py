from __future__ import annotations
from discord import slash_command, ApplicationContext, Option, message_command, InteractionContextType, Message, InputTextStyle
from src.client.embeds import ErrorEmbed, SuccessEmbed
import src.commands.autocomplete as autocomplete
from src.helpers import CustomModal
from .import_handler import ImportCommand
from src.db.models import ProxyTag
from .member import MemberCommands
from discord.ui import InputText
from .group import GroupCommands
from .base import BaseCommands
from asyncio import gather


class Commands(MemberCommands, GroupCommands, ImportCommand, BaseCommands):
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
        await ctx.response.send_message(
            f'menu management has not been implemented yet',
            ephemeral=True
        )

    @message_command(
        name='plural edit',
        contexts={InteractionContextType.guild})
    async def message_plural_edit(self, ctx: ApplicationContext, message: Message):
        if ctx.guild is None:
            return  # ? never going to happen mypy is just stupid

        if message.webhook_id is None:
            await ctx.response.send_message(
                embed=ErrorEmbed('message is not a proxied message!'),
                ephemeral=True
            )
            return

        webhook = await self.client.get_proxy_webhook(
            message.channel)  # type: ignore

        if message.webhook_id != webhook.id:
            await ctx.response.send_message(
                embed=ErrorEmbed('message is not a proxied message!'),
                ephemeral=True
            )
            return

        db_message = await self.client.db.message(
            proxy_id=message.id
        )

        if db_message is None:
            await ctx.response.send_message(
                embed=ErrorEmbed('message could not be found, is it too old?'),
                ephemeral=True
            )
            return

        if ctx.author.id != db_message.author_id:
            await ctx.response.send_message(
                embed=ErrorEmbed('you can only edit your own messages!'),
                ephemeral=True
            )
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
            await modal.interaction.response.send_message(
                embed=ErrorEmbed('no changes were made'),
                ephemeral=True
            )
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
            await ctx.response.send_message(
                embed=ErrorEmbed('you do not exist'),
                ephemeral=True
            )
            return

        if ctx.guild_id is None:
            return

        resolved_group = await self.client.db.group_by_name(
            ctx.interaction.user.id,
            group
        )

        if resolved_group is None:
            await ctx.response.send_message(
                embed=ErrorEmbed(f'group `{group}` not found'),
                ephemeral=True
            )
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
                await ctx.response.send_message(
                    embed=ErrorEmbed(
                        f'member `{member}` not found in group `{group}`'),
                    ephemeral=True
                )
                return

            latch.member = resolved_member.id

        if not latch.enabled:
            latch.member = None

        success_message = f'autoproxying is now {
            'enabled' if latch.enabled else 'disabled'}'

        if latch.enabled:
            success_message += f' and set to {
                f'member `{member}`'
                if member else
                'the next member to send a message'}'

        await gather(
            latch.save(),
            ctx.response.send_message(
                embed=SuccessEmbed(
                    success_message
                ),
                ephemeral=True
            )
        )

    @slash_command(
        name='delete_all_data',
        description='delete all your data; currently has NO CONFIRMATION')
    async def slash_delete_all_data(self, ctx: ApplicationContext):
        await ctx.response.defer(ephemeral=True)
        #! redo latches again to work with this system, _id is oid, include both user and guild

        groups = await self.client.db.groups(ctx.interaction.user.id)
        tasks = []
        for group in groups:
            members = await group.get_members()
            tasks.append(group.delete())
            for member in members:
                tasks.append(member.delete())
                if member.avatar:
                    avatar = await self.client.db.image(member.avatar)
                    if avatar:
                        tasks.append(avatar.delete())

        await gather(*tasks)

        await ctx.followup.send(  # ! also remember to replace these with send_error and send_success
            embed=SuccessEmbed('all your data has been deleted'),
            ephemeral=True
        )
