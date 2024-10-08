from discord import ApplicationContext, Option, SlashCommandGroup, Attachment, User
import src.commands.autocomplete as autocomplete
from src.helpers import send_error, send_success
from src.commands.base import BaseCommands
from discord.abc import GuildChannel
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
                name='group',
                description='name of the group',
                required=True)])
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
            send_success(ctx, f'created group `{group}`')
        )

    @group.command(
        name='remove',
        description='remove a group; group must have no members',
        options=[
            Option(
                str,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups)])
    async def group_remove(self, ctx: ApplicationContext, group: str):
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return

        if resolved_group.members:
            await send_error(ctx, f'group `{group}` has {len(resolved_group.members)} members')
            return

        await gather(
            resolved_group.delete(),
            send_success(ctx, f'deleted group `{group}`')
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
                str,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                User,
                name='user',
                description='account to share with')])
    async def group_share(self, ctx: ApplicationContext, group: str, user: User):
        ...  # ! figure out sharing groups with a code or something

    @group_set.command(
        name='name',
        description='set a group\'s name',
        options=[
            Option(
                str,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                str,
                name='name',
                description='new name for the group')])
    async def group_set_name(self, ctx: ApplicationContext, group: str, name: str):
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return

        resolved_group.name = name

        await gather(
            resolved_group.save(),
            send_success(ctx, f'set group `{group}` name to `{name}`')
        )

    @group_set.command(
        name='tag',
        description='set a group\'s tag',
        options=[
            Option(
                str,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                str,
                name='tag',
                description='tag for the group',
                required=False)])
    async def group_set_tag(self, ctx: ApplicationContext, group: str, tag: str | None):
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return

        resolved_group.tag = tag

        await gather(
            resolved_group.save(),
            send_success(ctx, f'set group `{group}` tag to `{tag}`')
        )

    @group_set.command(
        name='avatar',
        description='set a group\'s default avatar (4mb max, png, jpg, jpeg, gif, webp)',
        options=[
            Option(
                str,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                Attachment,
                name='avatar',
                description='avatar for the group',
                required=False)])
    async def group_set_avatar(self, ctx: ApplicationContext, group: str, avatar: Attachment | None):
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return

        if avatar is None:
            if resolved_group.avatar is not None:
                await ctx.response.defer(ephemeral=True)
                current_avatar = await self.client.db.image(resolved_group.avatar)
                if current_avatar is not None:
                    await current_avatar.delete()

            resolved_group.avatar = None

            await gather(
                resolved_group.save(),
                send_success(ctx, f'removed group `{group}` avatar')
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

        if resolved_group.avatar is not None:
            current_avatar = await self.client.db.image(resolved_group.avatar)
            if current_avatar is not None:
                await current_avatar.delete()

        resolved_group.avatar = image.id

        success_message = (
            f'group `{group}` now has avatar `{avatar.filename}`')
        if extension in {'gif'}:
            success_message += '\n\n**note:** gif avatars are not animated'

        await gather(
            resolved_group.save_changes(),
            send_success(ctx, success_message)
        )

    @group_channels.command(
        name='add',
        description='restrict a group to a channel',
        options=[
            Option(
                str,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                GuildChannel,
                name='channel',
                description='channel to add')])
    async def group_channels_add(self, ctx: ApplicationContext, group: str, channel: GuildChannel):
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return

        resolved_group.channels.add(channel.id)

        await gather(
            resolved_group.save(),
            send_success(ctx, f'added group `{
                         group}` to channel `{channel.name}`')
        )

    @group_channels.command(
        name='remove',
        description='remove a channel from a group',
        options=[
            Option(
                str,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups),
            Option(
                GuildChannel,
                name='channel',
                description='channel to remove')])
    async def group_channels_remove(self, ctx: ApplicationContext, group: str, channel: GuildChannel):
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return

        resolved_group.channels.discard(channel.id)

        await gather(
            resolved_group.save(),
            send_success(
                ctx,
                f'removed group `{group}` from channel `{channel.name}`')
        )

    @group_channels.command(
        name='list',
        description='list all channels a group is restricted to',
        options=[
            Option(
                str,
                name='group',
                description='name of the group',
                autocomplete=autocomplete.groups)])
    async def group_channels_list(self, ctx: ApplicationContext, group: str):
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return

        await send_success(ctx, '\n'.join(f'<#{channel}>' for channel in resolved_group.channels) or 'no channels')
