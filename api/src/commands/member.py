from __future__ import annotations

from asyncio import gather

from plural.db import Group, ProxyMember, Usergroup
from plural.errors import InteractionError
from plural.missing import MISSING

from src.components import PAGES
from src.core.models import env
from src.discord import (
    ApplicationCommandOptionType,
    ApplicationIntegrationType,
    InteractionContextType,
    ApplicationCommand,
    SlashCommandGroup,
    Interaction,
    Attachment,
    Embed
)

from .helpers import set_avatar, delete_avatar, delete_avatars, group_edit_check

from .userproxy import _userproxy_sync, _delete_userproxy


member = SlashCommandGroup(
    name='member',
    description='Manage your members',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL()
)

member_set = member.create_subgroup(
    name='set',
    description='Set member attributes'
)

member_tags = member.create_subgroup(
    name='tags',
    description='Manage a member\'s proxy tags'
)


@member.command(
    name='list',
    description='List all your members',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Restrict results to a single group; All groups if not specified',
            required=False,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_list(
    interaction: Interaction,
    group: Group | None = None
) -> None:
    await PAGES['pagination'](
        interaction,
        'member',
        group.id if group else None
    )


@member.command(
    name='new',
    description='Create a new member',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='Name of the member',
            required=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='meta',
            description='Custom identifier shown in autocomplete; Combination with name must be unique within a group',
            max_length=50,
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='Avatar for the member (max 4MB)',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='tag_prefix',
            description='Proxy tag prefix (e.g. {prefix}text)',
            max_length=50,
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='tag_suffix',
            description='Proxy tag suffix (e.g. text{suffix})',
            max_length=50,
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group to add the member to',
            required=False,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='simply_plural_id',
            description='Simply Plural ID to link to the member',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_new(
    interaction: Interaction,
    name: str,
    meta: str = '',
    avatar: Attachment | None = None,
    tag_prefix: str | None = None,
    tag_suffix: str | None = None,
    group: Group | None = None,
    simply_plural_id: str | None = None
) -> None:
    usergroup = await Usergroup.get_by_user(interaction.author_id)

    group = group or await Group.default(
        usergroup.id,
        interaction.author_id
    )

    group_edit_check(group, interaction.author_id, True)

    if await group.get_member_by_name(name, meta) is not None:
        error = [
            *(
                [f'Member `{name}` with meta `{meta}` already exists in group `{group.name}`']
                if meta else
                [f'Member `{name}` without meta field already exists in group `{group.name}`',
                 'Consider setting the meta field to make the member name unique',
                 f'See [the documentation](https://{env.domain}/guide/command-reference#member-new) for more information']
            ),
            'A name and meta combination must be unique within a group'
        ]

        raise InteractionError('\n\n'.join(error))

    member = ProxyMember(
        name=name,
        meta=meta,
        simply_plural_id=simply_plural_id,
    )

    if tag_prefix or tag_suffix:
        member.proxy_tags.append(
            ProxyMember.ProxyTag(
                prefix=tag_prefix or '',
                suffix=tag_suffix or ''
            )
        )

    if avatar is not None:
        await interaction.response.defer()
        await set_avatar(
            member,
            avatar.url,
            interaction.author_id
        )

    group.members.add(member.id)

    await gather(
        member.save(),
        group.save(),
        interaction.send(embeds=[Embed.success(
            title='Member Created',
            message=(
                f'Member `{name}` with meta `{meta}` created in group {group.name}'
                if meta else
                f'Member `{name}` created in group {group.name}'
            )
        )])
    )

    if simply_plural_id:
        await interaction.followup.send(
            embeds=[Embed.warning(
                title='Simply Plural Note',
                message='Simply Plural Integration is not yet implemented'
            ).set_footer(
                text='The ID you set has still been saved to the member'
            )]
        )


@member.command(
    name='remove',
    description='Remove a member',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to remove',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_remove(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    group.members.discard(member.id)

    if member.userproxy is not None:
        await _delete_userproxy(member)

    await gather(
        delete_avatar(member),
        member.delete(),
        group.save(),
        interaction.response.send_message(embeds=[Embed.success(
            title='Member Removed',
            message=f'Member `{member.name}` of group `{group.name}` has been deleted'
        )])
    )


@member_set.command(
    name='avatar',
    description='Set a member\'s avatar',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to give new avatar',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='New member avatar (4MB max)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_avatar(
    interaction: Interaction,
    member: ProxyMember,
    avatar: Attachment | None = None
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    await interaction.response.defer()

    if avatar:
        await set_avatar(member, avatar.url, interaction.author_id)
        message = f'Set member `{member.name}` avatar'
    else:
        await delete_avatar(member)
        message = f'Removed member `{member.name}` avatar'

    embed = Embed.success(
        message
    )

    if member.userproxy is not None:
        embed.set_footer(
            'Note: you may need to refresh your Discord client '
            'to see changes to userproxy bot'
        )

    await interaction.send(embeds=[embed])

    if member.userproxy is not None:
        await _userproxy_sync(
            interaction,
            member,
            {'avatar', 'icon'},
            silent=True
        )


@member_set.command(
    name='group',
    description='Set a member\'s group',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to move to new group',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='Group name',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_group(
    interaction: Interaction,
    member: ProxyMember,
    group: Group
) -> None:
    current_group = await member.get_group()

    group_edit_check(
        current_group,
        interaction.author_id
    )

    group_edit_check(
        group,
        interaction.author_id,
        True
    )

    if group.id == current_group.id:
        raise InteractionError(
            f'Member `{member.name}` is already in group `{group.name}`'
        )

    if await group.get_member_by_name(member.name, member.meta) is not None:
        raise InteractionError(
            f'Member `{member.name}` with meta `{member.meta}` already exists in group `{group.name}`'
        )

    current_group.members.discard(member.id)
    group.members.add(member.id)

    embed = Embed.success(
        title='Member Moved',
        message=f'Member `{member.name}` moved from group `{current_group.name}` to `{group.name}`'
    )

    if member.userproxy is not None:
        embed.set_footer(
            'Note: you may need to refresh your Discord client '
            'to see changes to userproxy bot'
        )

    await gather(
        current_group.save(),
        group.save(),
        interaction.response.send_message(embeds=[embed])
    )

    if member.userproxy is not None:
        await _userproxy_sync(
            interaction,
            member,
            {'username'},
            silent=True
        )


@member_set.command(
    name='meta',
    description='Set a member\'s meta field',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to give new meta field',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='meta',
            description='New member meta field (leave empty to remove)',
            max_length=50,
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_meta(
    interaction: Interaction,
    member: ProxyMember,
    meta: str | None = None
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    if await group.get_member_by_name(member.name, meta or '') is not None:
        raise InteractionError(
            f'Member `{member.name}` with meta `{meta}` already exists in group `{group.name}`'
            if meta else
            f'Member `{member.name}` without meta field already exists in group `{group.name}`'
        )

    member.meta = meta or ''

    await gather(
        member.save(),
        interaction.response.send_message(embeds=[Embed.success(
            title='Member Meta Updated',
            message=(
                f'Member `{member.name}` meta field changed to `{meta}`'
                if meta else
                f'Member `{member.name}` meta field removed'
            )
        )])
    )


@member_set.command(
    name='name',
    description='Set a member\'s name',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to give new name',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='New member name',
            max_length=80,
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_name(
    interaction: Interaction,
    member: ProxyMember,
    name: str
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    if await group.get_member_by_name(name, member.meta) is not None:
        raise InteractionError(
            f'Member `{name}` with meta `{member.meta}` already exists in group `{group.name}`'
            if member.meta else
            f'Member `{name}` without meta field already exists in group `{group.name}`'
        )

    if member.userproxy is not None:
        usergroup = await Usergroup.get_by_user(interaction.author_id)

        userproxy_name = name + (
            (group.tag or '')
            if usergroup.userproxy_config.include_group_tag
            else ''
        )

        if not (2 <= len(userproxy_name) <= 32):
            raise InteractionError(
                'Userproxy member names must be between 2 and 32 characters '
                '(including group tag, if enabled)'
            )

    old_name, member.name = member.name, name

    embed = Embed.success(
        title='Member Name Changed',
        message=f'Member `{old_name}` of group `{group.name}` renamed to `{name}`'
    )

    if member.userproxy is not None:
        embed.set_footer(
            'Note: you may need to refresh your Discord client '
            'to see changes to userproxy bot'
        )

    await gather(
        member.save(),
        interaction.response.send_message(embeds=[embed])
    )

    if member.userproxy is not None:
        await _userproxy_sync(
            interaction,
            member,
            {'username'},
            silent=True
        )


@member_set.command(
    name='pronouns',
    description='Set a member\'s pronouns',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to give new pronouns',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='pronouns',
            description='New member pronouns',
            max_length=50,
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_pronouns(
    interaction: Interaction,
    member: ProxyMember,
    pronouns: str = ''
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    member.pronouns = pronouns

    await gather(
        member.save(),
        interaction.response.send_message(embeds=[Embed.success(
            title='Member Pronouns Updated',
            message=(
                f'Member `{member.name}` pronouns changed to `{pronouns}`'
                if pronouns else
                f'Member `{member.name}` pronouns removed'
            )
        )])
    )


@member_tags.command(
    name='add',
    description='Add a proxy tag to a member (15 max)',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to add tag to',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='prefix',
            description='Proxy tag prefix (e.g. {prefix}text)',
            max_length=50,
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='suffix',
            description='Proxy tag suffix (e.g. text{suffix})',
            max_length=50,
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='regex',
            description='Whether the proxy tag is matched with regex (default: False)',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='case_sensitive',
            description='Whether the proxy tag is case sensitive (default: False)',
            required=False),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='Avatar for the proxy tag (4MB max)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_tags_add(
    interaction: Interaction,
    member: ProxyMember,
    prefix: str | None = None,
    suffix: str | None = None,
    regex: bool = False,
    case_sensitive: bool = False,
    avatar: Attachment | None = None
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    if len(member.proxy_tags) >= 15:
        raise InteractionError(
            'Members can only have a maximum of 15 proxy tags'
        )

    if prefix is None and suffix is None:
        raise InteractionError(
            'Proxy tags must have a prefix and/or suffix'
        )

    proxy_tag = ProxyMember.ProxyTag(
        prefix=prefix or '',
        suffix=suffix or '',
        regex=regex,
        case_sensitive=case_sensitive
    )

    if proxy_tag in member.proxy_tags:
        raise InteractionError(
            f'Member `{member.name}` already has this proxy tag'
        )

    member.proxy_tags.append(proxy_tag)

    if avatar is not None:
        await interaction.response.defer()
        await set_avatar(
            member,
            avatar.url,
            interaction.author_id,
            member.proxy_tags.index(proxy_tag)
        )

    await gather(
        member.save(),
        interaction.send(embeds=[Embed.success(
            title='Proxy Tag Added',
            message=f'Proxy tag {proxy_tag.name} added to member `{member.name}`'
        )])
    )


@member_tags.command(
    name='avatar',
    description='Edit a proxy tag avatar',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to add tag to',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_tag',
            description='Proxy tag to edit',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='Avatar for the proxy tag (4MB max) (leave empty to remove)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_tags_avatar(
    interaction: Interaction,
    member: ProxyMember,
    proxy_tag: int,
    avatar: Attachment | None = None
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    await interaction.response.defer()

    tag_index, tag = proxy_tag, member.proxy_tags[proxy_tag]

    if avatar is not None:
        await set_avatar(
            member,
            avatar.url,
            interaction.author_id,
            tag_index)
        message = f'Set Proxy Tag {tag.name} avatar'
    else:
        await delete_avatar(member, tag_index)
        message = f'Removed Proxy Tag {tag.name} avatar'

    await interaction.send(embeds=[Embed.success(
        title='Proxy Tag Edited',
        message=message
    )])


@member_tags.command(
    name='clear',
    description='Clear all proxy tags from a member',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to clear tags from',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_tags_clear(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    avatars = [
        index
        for index, tag in enumerate(member.proxy_tags)
        if tag.avatar is not None
    ]

    if avatars:
        await interaction.response.defer()

        await delete_avatars([
            (member, index)
            for index in avatars
        ])

    member.proxy_tags.clear()

    await gather(
        member.save(),
        interaction.send(embeds=[Embed.success(
            title='Proxy Tags Cleared',
            message=f'All proxy tags removed from member `{member.name}`'
        )])
    )


@member_tags.command(
    name='list',
    description='List a member\'s proxy tags',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to list tags of',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_tags_list(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    has_avatars = any(
        tag.avatar is not None
        for tag in
        member.proxy_tags
    )

    padding = len(str(len(member.proxy_tags))) + 3 + has_avatars

    def padded(index: int, avatar: bool) -> str:
        return f'`{index}{'a' if avatar else ''}`'.ljust(
            padding
        ).replace(
            ' ', ' ​'
        ).strip('​')

    embed = Embed.success(
        title='Member Proxy Tags',
        message='\n'.join([
                f'{padded(index + 1, tag.avatar is not None)}{tag.name}'
                for index, tag in enumerate(member.proxy_tags)
        ]) or 'No proxy tags'
    ).set_author(
        name=member.name,
        icon_url=(
            member.avatar_url or
            (await member.get_group()).avatar_url or
            MISSING
        )
    )

    if has_avatars:
        embed.set_footer(
            text='Tags with an `a` have an avatar overwrite'
        )

    await interaction.response.send_message(
        embeds=[embed]
    )


@member_tags.command(
    name='remove',
    description='Remove a proxy tag from a member',
    options=[
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='Member to remove tag from',
            required=True,
            autocomplete=True),
        ApplicationCommand.Option(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_tag',
            description='Proxy tag to remove',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_tags_remove(
    interaction: Interaction,
    member: ProxyMember,
    proxy_tag: int
) -> None:
    group = await member.get_group()

    group_edit_check(group, interaction.author_id)

    if member.proxy_tags[proxy_tag].avatar is not None:
        await interaction.response.defer()
        await delete_avatar(member, proxy_tag)

    tag = member.proxy_tags.pop(proxy_tag)

    await gather(
        member.save(),
        interaction.send(embeds=[Embed.success(
            title='Proxy Tag Removed',
            message=f'Proxy tag {tag.name} removed from member `{member.name}`'
        )])
    )
