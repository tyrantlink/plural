from discord import ApplicationContext, Option, SlashCommandGroup, Attachment, User
from src.helpers import send_error, send_success, DBConverter, include_all_options
import src.commands.autocomplete as autocomplete
from src.commands.base import BaseCommands
from discord.abc import GuildChannel
from src.db import Group, Member
from asyncio import gather


class GroupCommands(BaseCommands):
    group = SlashCommandGroup(
        name='group',
        description='manage a group'
    )
    group_set = group.create_subgroup(
        name='set',
        description='set a group\'s attributes'
    )
    group_channels = group.create_subgroup(
        name='channels',
        description='manage a group\'s channels'
    )

    @group.command(
        name='new',
        description='create a new group',
        options=[
            Option(
                str,
                name='name',
                description='name of the new group')])
    async def group_new(self, ctx: ApplicationContext, group: str):
        if await self.client.db.group_by_name(ctx.author.id, group) is not None:
            await send_error(ctx, f'group `{group}` already exists')
            return

        new_group = self.client.db.new.group(
            name=group
        )

        new_group.accounts.add(ctx.author.id)

        await gather(
            new_group.save(),
            send_success(ctx, f'created group `{new_group.name}`')
        )

    @group.command(
        name='remove',
        description='remove a group; group must have no members',
        options=[
            Option(
                DBConverter,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups)])
    async def group_remove(self, ctx: ApplicationContext, group: Group):
        if group.members:
            await send_error(ctx, f'group `{group}` has {len(group.members)} members\nremove all members before deleting')
            return

        await gather(
            group.delete(),
            send_success(ctx, f'deleted group `{group.name}`')
        )

    @group.command(
        name='list',
        description='list all groups')
    async def group_list(self, ctx: ApplicationContext):
        groups = await self.client.db.groups(ctx.author.id)

        await send_success(ctx, '\n'.join(group.name for group in groups) or 'no groups')

    @group.command(
        name='share',
        description='share a group with another account',
        options=[
            Option(
                DBConverter,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                User,
                name='user',
                description='account to share with')])
    async def group_share(self, ctx: ApplicationContext, group: Group, user: User):
        # ! figure out sharing groups with a code or something
        await send_error(ctx, 'not implemented')

    @group_set.command(
        name='name',
        description='set a group\'s name',
        options=[
            Option(
                DBConverter,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                str,
                name='name',
                description='new name for the group')])
    async def group_set_name(self, ctx: ApplicationContext, group: Group, name: str):
        old_name, group.name = group.name, name

        await gather(
            group.save(),
            send_success(ctx, f'set group `{old_name}` name to `{group.name}`')
        )

    @group_set.command(
        name='tag',
        description='set a group\'s tag',
        options=[
            Option(
                DBConverter,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                str,
                name='tag',
                description='tag for the group',
                required=False)])
    async def group_set_tag(self, ctx: ApplicationContext, group: Group, tag: str | None):
        group.tag = tag

        await gather(
            group.save(),
            send_success(ctx, f'set group `{group.name}` tag to `{tag}`')
        )

    @group_set.command(
        name='avatar',
        description='set a group\'s default avatar (4mb max, png, jpg, jpeg, gif, webp)',
        options=[
            Option(
                DBConverter,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                Attachment,
                name='avatar',
                description='avatar for the group',
                required=False)])
    async def group_set_avatar(self, ctx: ApplicationContext, group: Group, avatar: Attachment | None):
        if avatar is None:
            if group.avatar is not None:
                await ctx.response.defer(ephemeral=True)
                current_avatar = await self.client.db.image(group.avatar)
                if current_avatar is not None:
                    await current_avatar.delete()

            group.avatar = None

            await gather(
                group.save(),
                send_success(ctx, f'removed group `{group.name}` avatar')
            )
            return None

        extension = avatar.filename.rsplit('.', 1)[-1]

        if extension not in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
            await send_error(ctx, 'avatar must be a png, jpg, jpeg, gif, or webp')
            return None

        if avatar.size > 4_194_304:
            await send_error(ctx, 'avatar size must be less than 4mb')
            return None

        await ctx.response.defer(ephemeral=True)

        image = self.client.db.new.image(await avatar.read(), extension)

        await image.save()

        if group.avatar is not None:
            current_avatar = await self.client.db.image(group.avatar)
            if current_avatar is not None:
                await current_avatar.delete()

        group.avatar = image.id

        success_message = (
            f'group `{group.name}` now has avatar `{avatar.filename}`')
        if extension in {'gif'}:
            success_message += '\n\n**note:** gif avatars are not animated'

        await gather(
            group.save_changes(),
            send_success(ctx, success_message)
        )

    @group_channels.command(
        name='add',
        description='restrict a group to a channel',
        options=[
            Option(
                DBConverter,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                GuildChannel,
                name='channel',
                description='channel to add')])
    async def group_channels_add(self, ctx: ApplicationContext, group: Group, channel: GuildChannel):
        group.channels.add(channel.id)

        await gather(
            group.save(),
            send_success(
                ctx,
                f'added group `{group.name}` to channel `{channel.mention}`')
        )

    @group_channels.command(
        name='remove',
        description='remove a channel from a group',
        options=[
            Option(
                DBConverter,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                GuildChannel,
                name='channel',
                description='channel to remove')])
    async def group_channels_remove(self, ctx: ApplicationContext, group: Group, channel: GuildChannel):
        group.channels.discard(channel.id)

        await gather(
            group.save(),
            send_success(
                ctx,
                f'removed group `{group.name}` from channel `{channel.name}`')
        )

    @group_channels.command(
        name='list',
        description='list all channels a group is restricted to',
        options=[
            Option(
                DBConverter,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups)])
    async def group_channels_list(self, ctx: ApplicationContext, group: Group):
        await send_success(
            ctx,
            '\n'.join(
                f'<#{channel}>'
                for channel in
                group.channels
            ) or
            'no channels'
        )
