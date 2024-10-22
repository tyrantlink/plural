from discord import ApplicationContext, Option, SlashCommandGroup, Attachment, HTTPException, InputTextStyle
from src.models import MemberUpdateType, USERPROXY_FOOTER_LIMIT, USERPROXY_FOOTER
from src.converters import MemberConverter, GroupConverter, include_all_options
from src.helpers import send_error, send_success, multi_request, CustomModal
import src.commands.autocomplete as autocomplete
from discord.utils import _bytes_to_base64_data
from src.commands.base import BaseCommands
from src.db.models import ProxyTag
from discord.ui import InputText
from src.db import Member, Group
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

    async def _on_member_update(
        self,
        ctx: ApplicationContext,
        member: Member,
        type: MemberUpdateType
    ) -> None:
        print('on_member_update')
        assert ctx.interaction.user is not None
        if (userproxy := await member.get_userproxy()) is None:
            return None

        if userproxy.token is None:

            return None

        patches: list[tuple[str, str, dict | None]] = []

        match type:
            case MemberUpdateType.NAME:
                patches = [
                    ('patch', 'users/@me', {'username': member.name})
                ]
            case MemberUpdateType.AVATAR:
                image_data = None

                if member.avatar:
                    image = await self.client.db.image(member.avatar, True)
                    if image is not None:
                        image_data = _bytes_to_base64_data(image.data)

                patches = [
                    ('patch', 'users/@me', {'avatar': image_data}),
                    ('patch', 'applications/@me', {'icon': image_data})
                ]
            case MemberUpdateType.DESCRIPTION:
                description = f'{member.description or ""}\n\n{
                    USERPROXY_FOOTER.format(username=ctx.interaction.user.name)}'.strip()
                patches = [
                    ('patch', 'applications/@me',
                     {'description': description})
                ]
            case _:
                return None

        if patches:
            try:
                await multi_request(
                    userproxy.token,
                    patches  # type: ignore # ? i don't wanna deal with mypy right now
                )
            except HTTPException as exception:
                error = exception.text
                code = 'UNKNOWN'
                try:  # ? this is really really gross
                    json_error: dict[str, dict[str, dict[str, list[dict[str, str]]]]] = await exception.response.json()
                    error_detail = list(
                        list(
                            json_error['errors'].values()
                        )[0].values())[0][0]
                    code = error_detail['code']
                    error = error_detail['message']
                except Exception:
                    pass

                match code:
                    case 'UNKNOWN':
                        print(
                            f'got unknown error code from discord on auto sync: {code}, {error}')
                    case 'USERNAME_TOO_MANY_USERS':
                        error += '\n\n**note**: username is still updated for the /plu/ral member'

                await send_error(ctx, f'error updating userproxy: {error}')

    @member.command(
        name='new',
        description='create a new member',
        checks=[include_all_options],
        options=[
            Option(
                str,
                name='name',
                max_length=50,
                description='the name of the member'),
            Option(
                GroupConverter,
                name='group',
                description='the name of the group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_new(self, ctx: ApplicationContext, name: str, group: Group) -> None:
        if await group.get_member_by_name(name) is not None:
            await send_error(ctx, f'member `{name}` already exists')
            return None

        if group.tag is not None:
            if len(name+group.tag) > 80:
                await send_error(ctx, f'member name and group tag combined must be less than 80 characters')
                return None

        await group.add_member(name)

        await send_success(ctx, f'created member `{name}` in group `{group.name}`')

    @member.command(
        name='delete',
        description='delete a member',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_delete(self, ctx: ApplicationContext, member: Member, group: Group) -> None:
        await group.delete_member(member.id)

        await send_success(ctx, f'member `{member.name}` of group `{group.name}` was deleted')

    @member.command(
        name='list',
        description='list all members in a group',
        checks=[include_all_options],
        options=[
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_list(self, ctx: ApplicationContext, group: Group) -> None:
        members = await group.get_members()

        member_list = '\n'.join([
            member.name
            for member
            in members
        ]) or 'no members found'

        await send_success(ctx, f'members in group `{group.name}`:\n{member_list}')

    @member_set.command(
        name='name',
        description='set a member\'s name',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='name',
                max_length=50,
                description='the new name of the member'),
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_set_name(self, ctx: ApplicationContext, member: Member, name: str, group: Group) -> None:
        old_name, member.name = member.name, name

        updated_member, _ = await gather(
            member.save_changes(),
            send_success(
                ctx,
                f'member `{old_name}` of group `{group.name}` was renamed to `{member.name}`')
        )
        if updated_member is not None:
            await self._on_member_update(ctx, updated_member, MemberUpdateType.NAME)

    @member_set.command(
        name='group',
        description='set a member\'s group',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                GroupConverter,
                name='new_group',
                description='the name of the new group',
                autocomplete=autocomplete.groups),
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_set_group(self, ctx: ApplicationContext, member: Member, new_group: Group, group: Group) -> None:
        group.members.remove(member.id)
        new_group.members.add(member.id)

        await gather(
            group.save_changes(),
            new_group.save_changes(),
            send_success(
                ctx,
                f'member `{member.name}` of group `{group.name}` was moved to group `{new_group.name}`')
        )

    @member_set.command(
        name='avatar',
        description='set a member\'s avatar (4mb max, png, jpg, jpeg, gif, webp)',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                Attachment,
                name='avatar',
                required=False,
                description='the avatar of the member'),
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_set_avatar(
        self,
        ctx: ApplicationContext,
        member: Member,
        avatar: Attachment | None,
        group: Group
    ) -> None:
        if avatar is None:
            if member.avatar is not None:
                await ctx.response.defer(ephemeral=True)
                current_avatar = await self.client.db.image(member.avatar)
                if current_avatar is not None:
                    await current_avatar.delete()

            member.avatar = None

            await gather(
                member.save_changes(),
                send_success(
                    ctx,
                    f'member `{member.name}` of group `{group.name}` now has no avatar')
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

        if member.avatar is not None:
            current_avatar = await self.client.db.image(member.avatar)
            if current_avatar is not None:
                await current_avatar.delete()

        member.avatar = image.id

        success_message = (
            f'member `{member.name}` of group `{group.name}` now has avatar `{avatar.filename}`')
        if extension in {'gif'}:
            success_message += '\n\n**note:** gif avatars are not animated'

        updated_member, _ = await gather(
            member.save_changes(),
            send_success(ctx, success_message)
        )
        if updated_member is not None:
            await self._on_member_update(ctx, updated_member, MemberUpdateType.AVATAR)

    @member_set.command(
        name='description',
        description='set a member\'s description (will be set in pop up modal)',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_set_description(
        self,
        ctx: ApplicationContext,
        member: Member,
        group: Group
    ) -> None:
        modal = CustomModal(
            title='set member description',
            children=[
                InputText(
                    max_length=USERPROXY_FOOTER_LIMIT,
                    value=member.description or '',
                    placeholder='description',
                    style=InputTextStyle.long,
                    label='description',
                    required=False
                )
            ]
        )

        await ctx.response.send_modal(modal)

        await modal.wait()

        description = modal.children[0].value or None

        member.description = description

        updated_member, _ = await gather(
            member.save_changes(),
            send_success(
                modal.interaction,
                f'member `{member.name}` of group `{group.name}` now has description `{description}`')
        )

        if updated_member is not None:
            await self._on_member_update(ctx, updated_member, MemberUpdateType.DESCRIPTION)

    @member_proxy.command(
        name='add',
        description='add a proxy tag to a member',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
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
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_proxy_add(
        self,
        ctx: ApplicationContext,
        member: Member,
        prefix: str | None,
        suffix: str | None,
        regex: bool,
        group: Group
    ) -> None:
        if len(member.proxy_tags) >= 5:
            await send_error(ctx, 'a member can only have up to 5 proxy tags')
            return None

        member.proxy_tags.append(
            ProxyTag(
                prefix=prefix or '',
                suffix=suffix or '',
                regex=regex
            )
        )

        await gather(
            member.save_changes(),
            send_success(
                ctx,
                f'proxy tag added to member `{member.name}` of group `{group.name}`')
        )

    @member_proxy.command(
        name='remove',
        description='remove a proxy tag from a member',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                int,  # ! make an autocomplete for this {prefix}text{suffix}
                name='proxy_index',
                min_value=0,
                max_value=4,
                description='the index of the proxy tag to remove (check with /member proxy list)'),
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_proxy_remove(
        self,
        ctx: ApplicationContext,
        member: Member,
        tag_index: int,
        group: Group
    ) -> None:
        if tag_index < 0 or tag_index >= len(member.proxy_tags):
            await send_error(ctx, 'proxy tag index out of range')
            return None

        member.proxy_tags.pop(tag_index)

        await gather(
            member.save_changes(),
            send_success(
                ctx,
                f'proxy tag removed from member `{member.name}` of group `{group.name}`')
        )

    @member_proxy.command(
        name='list',
        description='list all proxy tags of a member',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_proxy_list(
        self,
        ctx: ApplicationContext,
        member: Member,
        group: Group
    ) -> None:
        tags = '\n'.join([
            f'`{index}{" (regex)" if tag.regex else ""}`: {
                tag.prefix}text{tag.suffix}'
            for index, tag
            in enumerate(member.proxy_tags)
        ]) or 'no proxy tags set'

        await send_success(ctx, f'proxy tags of member `{member.name}` in group `{group.name}`:\n{tags}')

    @member_proxy.command(
        name='clear',
        description='clear all proxy tags of a member',
        checks=[include_all_options],
        options=[
            Option(
                MemberConverter,
                name='member',
                description='the name of the member',
                autocomplete=autocomplete.members),
            Option(
                GroupConverter,
                name='group',
                description='restrict results to a single group',
                required=False,
                autocomplete=autocomplete.groups)])
    async def slash_member_proxy_clear(
        self,
        ctx: ApplicationContext,
        member: Member,
        group: Group
    ) -> None:
        member.proxy_tags.clear()

        await gather(
            member.save_changes(),
            send_success(
                ctx,
                f'all proxy tags removed from member `{member.name}` of group `{group.name}`')
        )
