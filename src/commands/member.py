from discord import ApplicationContext, Option, SlashCommandGroup, Attachment
import src.commands.autocomplete as autocomplete
from src.helpers import send_error, send_success
from src.commands.base import BaseCommands
from src.db.models import ProxyTag
from src.db import Group, Member
from asyncio import gather


class MemberCommands(BaseCommands):
    member = SlashCommandGroup(
        name='member',
        description='manage a member'
    )
    member_set = member.create_subgroup(
        name='set',
        description='set a member\'s attributes'
    )
    member_proxy = member.create_subgroup(
        name='proxy',
        description='manage a member\'s proxy tags'
    )

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

    async def _base_member_getter(self, interaction: ApplicationContext, group: str, member: str) -> tuple[Group, Member] | tuple[None, None]:
        resolved_group = await self._base_group_getter(interaction, group)

        if resolved_group is None:
            return None, None

        resolved_member = await resolved_group.get_member_by_name(member)

        if resolved_member is None:
            await send_error(interaction, f'member `{member}` not found')
            return None, None

        return resolved_group, resolved_member

    @member.command(
        name='new',
        description='create a new member',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member'),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_new(self, ctx: ApplicationContext, member: str, group: str) -> None:
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return None

        if await resolved_group.get_member_by_name(member) is not None:
            await send_error(ctx, f'member `{member}` already exists')
            return None

        await resolved_group.add_member(member)

        await send_success(ctx, f'created member `{member}` in group `{group}`')

    @member.command(
        name='delete',
        description='delete a member',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_delete(self, ctx: ApplicationContext, member: str, group: str) -> None:
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return None

        await resolved_group.delete_member(resolved_member.id)

        await send_success(ctx, f'member `{member}` of group `{group}` was deleted')

    @member.command(
        name='list',
        description='list all members in a group',
        options=[
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_list(self, ctx: ApplicationContext, group: str) -> None:
        resolved_group = await self._base_group_getter(ctx, group)

        if resolved_group is None:
            return None

        members = await resolved_group.get_members()

        member_list = '\n'.join([
            member.name
            for member
            in members
        ]) or 'no members found'

        await send_success(ctx, f'members in group `{group}`:\n{member_list}')

    @member_set.command(
        name='name',
        description='set a member\'s name',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='name',
                description='the new name of the member'),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_set_name(self, ctx: ApplicationContext, member: str, name: str, group: str) -> None:
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return None

        resolved_member.name = name

        await gather(
            resolved_member.save_changes(),
            send_success(
                ctx,
                f'member `{member}` of group `{group}` was renamed to `{name}`')
        )

    @member_set.command(
        name='group',
        description='set a member\'s group',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='new_group',
                description='the name of the new group',
                autocomplete=autocomplete.groups),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_set_group(self, ctx: ApplicationContext, member: str, new_group: str, group: str) -> None:
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return None

        new_resolved_group = await self._base_group_getter(ctx, new_group)

        if new_resolved_group is None:
            return None

        resolved_group.members.remove(resolved_member.id)
        new_resolved_group.members.add(resolved_member.id)

        await gather(
            resolved_group.save_changes(),
            new_resolved_group.save_changes(),
            send_success(
                ctx,
                f'member `{member}` of group `{group}` was moved to group `{new_group}`')
        )

    @member_set.command(
        name='avatar',
        description='set a member\'s avatar (4mb max, png, jpg, jpeg, gif, webp)',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                Attachment,
                name='avatar',
                required=False,
                description='the avatar of the member'),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_set_avatar(self, ctx: ApplicationContext, member: str, avatar: Attachment | None, group: str) -> None:
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return None

        if avatar is None:
            if resolved_member.avatar is not None:
                await ctx.response.defer(ephemeral=True)
                current_avatar = await self.client.db.image(resolved_member.avatar)
                if current_avatar is not None:
                    await current_avatar.delete()

            resolved_member.avatar = None

            await gather(
                resolved_member.save_changes(),
                send_success(
                    ctx,
                    f'member `{member}` of group `{group}` now has no avatar')
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

        if resolved_member.avatar is not None:
            current_avatar = await self.client.db.image(resolved_member.avatar)
            if current_avatar is not None:
                await current_avatar.delete()

        resolved_member.avatar = image.id

        success_message = (
            f'member `{member}` of group `{group}` now has avatar `{avatar.filename}`')
        if extension in {'gif'}:
            success_message += '\n\n**note:** gif avatars are not animated'

        await gather(
            resolved_member.save_changes(),
            send_success(ctx, success_message)
        )

    @member_proxy.command(
        name='add',
        description='add a proxy tag to a member',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='prefix',
                description='the prefix of the proxy tag',
                required=False),
            Option(
                str,
                name='suffix',
                description='the suffix of the proxy tag',
                required=False),
            Option(
                bool,
                name='regex',
                description='whether the proxy tag is matched with regex',
                default=False),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_proxy_add(
        self,
        ctx: ApplicationContext,
        member: str,
        prefix: str | None,
        suffix: str | None,
        regex: bool,
        group: str
    ) -> None:
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return None

        if len(resolved_member.proxy_tags) >= 5:
            await send_error(ctx, 'a member can only have up to 5 proxy tags')
            return None

        resolved_member.proxy_tags.append(
            ProxyTag(
                prefix=prefix or '',
                suffix=suffix or '',
                regex=regex
            )
        )

        await gather(
            resolved_member.save_changes(),
            send_success(
                ctx,
                f'proxy tag added to member `{member}` of group `{group}`')
        )

    @ member_proxy.command(
        name='remove',
        description='remove a proxy tag from a member',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                int,
                name='proxy_index',
                min_value=0,
                max_value=4,
                description='the index of the proxy tag to remove (check with /member proxy list)'),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_proxy_remove(
        self,
        ctx: ApplicationContext,
        member: str,
        tag_index: int,
        group: str
    ) -> None:
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return None

        if tag_index < 0 or tag_index >= len(resolved_member.proxy_tags):
            await send_error(ctx, 'proxy tag index out of range')
            return None

        resolved_member.proxy_tags.pop(tag_index)

        await gather(
            resolved_member.save_changes(),
            send_success(
                ctx,
                f'proxy tag removed from member `{member}` of group `{group}`')
        )

    @member_proxy.command(
        name='list',
        description='list all proxy tags of a member',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_proxy_list(
        self,
        ctx: ApplicationContext,
        member: str,
        group: str
    ) -> None:
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return None

        tags = '\n'.join([
            f'`{index}{" (regex)" if tag.regex else ""}`: {
                tag.prefix} text {tag.suffix}'
            for index, tag
            in enumerate(resolved_member.proxy_tags)
        ]) or 'no proxy tags set'

        await send_success(ctx, f'proxy tags of member `{member}` in group `{group}`:\n{tags}')

    @member_proxy.command(
        name='clear',
        description='clear all proxy tags of a member',
        options=[
            Option(
                str,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='group',
                description='the name of the group',
                default='default',
                autocomplete=autocomplete.groups)])
    async def slash_member_proxy_clear(
        self,
        ctx: ApplicationContext,
        member: str,
        group: str
    ) -> None:
        resolved_group, resolved_member = await self._base_member_getter(ctx, group, member)

        if resolved_group is None or resolved_member is None:
            return None

        resolved_member.proxy_tags.clear()

        await gather(
            resolved_member.save_changes(),
            send_success(
                ctx,
                f'all proxy tags removed from member `{member}` of group `{group}`')
        )
