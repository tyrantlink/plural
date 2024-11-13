from src.discord import slash_command, Interaction, message_command, InteractionContextType, Message, ApplicationCommandOption, ApplicationCommandOptionType, Embed, Permission, ApplicationIntegrationType, ApplicationCommandOptionChoice, Attachment, SlashCommandGroup
from src.db import Message as DBMessage, ProxyMember, Latch, UserProxyInteraction, Group, Image, ProxyTag
from src.models import USERPROXY_FOOTER, USERPROXY_FOOTER_LIMIT
from src.logic.proxy import get_proxy_webhook, process_proxy
from src.logic.modals import modal_plural_edit, umodal_edit
from src.discord.http import _get_mime_type_for_image
from src.errors import InteractionError
from asyncio import gather
from time import time

#! when syncing userproxies, replace the interactions endpoint url


member = SlashCommandGroup(
    name='member',
    description='manage your members',
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL()
)

member_set = member.create_subgroup(
    name='set',
    description='set member properties'
)

member_proxy_tags = member.create_subgroup(
    name='proxy_tags',
    description='manage a member\'s proxy tags'
)

member_userproxy = member.create_subgroup(
    name='userproxy',
    description='manage a member\'s userproxy'
)


@member.command(
    name='new',
    description='create a new member',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='name of the member',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to add the member to',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_new(
    interaction: Interaction,
    name: str,
    group: Group | None = None
) -> None:
    group = group or await Group.get_or_create_default(interaction.author_id)

    if group.get_member_by_name(name) is not None:
        raise InteractionError(
            f'member {name} already exists in group {group.name}')

    embeds = [
        Embed.success(f'member {name} created in group {group.name}')
    ]

    if group.tag is not None:
        if len(name+group.tag) > 80:
            embeds.append(Embed.warning('\n\n'.join([
                f'member name with group tag is longer than 80 characters.',
                'display name will be truncated when proxying'
            ])))

    await group.add_member(name)

    await interaction.response.send_message(embeds=embeds)


@member.command(  # ! add pagination
    name='list',
    description='list members',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group to list members for (default: default)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_list(
    interaction: Interaction,
    group: Group | None = None
) -> None:
    group = group or await Group.get_or_create_default(interaction.author_id)

    await interaction.response.send_message(
        embeds=[
            Embed.success(
                title=f'members in group {group.name}',
                message='\n'.join([
                    f'{member.name}'
                    for member in await group.get_members()
                ]) or 'this group has no members'
            )
        ]
    )


@member.command(
    name='remove',
    description='remove a member',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to remove',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_remove(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    group = await member.get_group()
    await group.delete_member(member.id)

    await interaction.response.send_message(
        embeds=[Embed.success(
            f'member `{member.name}` of group `{group.name}` was deleted'
        )]
    )


@member_set.command(  # ! remember userproxy auto syncing
    name='name',
    description='set a member\'s name',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to give new name',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='new member name',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_name(
    interaction: Interaction,
    member: ProxyMember,
    name: str
) -> None:
    old_name, member.name = member.name, name

    group = await member.get_group()

    await gather(
        member.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'member `{old_name}` of group `{group.name}` was renamed to `{name}`'
            )]
        ))


@member_set.command(
    name='group',
    description='set a member\'s group',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to move to new group',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group name',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_group(
    interaction: Interaction,
    member: ProxyMember,
    group: Group
) -> None:
    old_group = await member.get_group()

    old_group.members.remove(member.id)
    group.members.add(member.id)

    await gather(
        old_group.save(),
        group.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'member `{member.name}` of group `{old_group.name}` was moved from group `{group.name}`'
            )]
        )
    )


@member_set.command(  # ! remember userproxy auto syncing
    name='avatar',
    description='set a member\'s avatar',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to give new avatar',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='new member avatar',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_avatar(
    interaction: Interaction,
    member: ProxyMember,
    avatar: Attachment
) -> None:
    if avatar is None:
        current_avatar, member.avatar = member.avatar, avatar

        await gather(
            member.save(),
            Image.find({'_id': current_avatar}).delete(),
            interaction.response.send_message(
                embeds=[Embed.success(
                    f'removed member `{member.name}` avatar')]
            )
        )
        return

    if avatar.size > 4_194_304:
        raise InteractionError('avatars must be less than 4MB')

    await interaction.response.defer()

    if avatar.filename.rsplit('.', 1)[-1].lower() not in {'png', 'jpeg', 'jpg', 'gif', 'webp'}:
        raise InteractionError('avatars must be a png, jpg, gif, or webp')

    data = await avatar.read()

    try:
        mime_type = _get_mime_type_for_image(data[:16])
    except ValueError:
        raise InteractionError('invalid format; image may be corrupted')

    image = await Image(
        data=data,
        extension=mime_type.split('/')[-1]
    ).save()

    current_avatar, member.avatar = member.avatar, image.id

    response = f'group `{member.name}` now has the avatar `{avatar.filename}`'

    if mime_type == 'image/gif':
        response += '\n\n**note:** gif avatars are not animated'

    await gather(
        member.save(),
        Image.find({'_id': current_avatar}).delete(),
        interaction.response.send_message(
            embeds=[Embed.success(response)]
        )
    )


@member_set.command(  # ! userproxy only; make modal
    name='bio',
    description='set a member\'s bio (userproxies only)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            max_length=USERPROXY_FOOTER_LIMIT,
            description='member to give new bio',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='bio',
            description='new member bio',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='include_attribution',
            description='whether to add "userproxy for @user, powered by /plu/ral" to the end of the bio',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_bio(
    interaction: Interaction,
    member: ProxyMember,
    bio: str,
    include_attribution: bool = True
) -> None:
    ...


@member_set.command(  # ! userproxy only
    name='banner',
    description='set a member\'s banner (userproxies only)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to give new banner',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='banner',
            description='new member banner',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_banner(
    interaction: Interaction,
    member: ProxyMember,
    banner: Attachment
) -> None:
    ...


@member_proxy_tags.command(
    name='add',
    description='add proxy tags to a member (15 max)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to add tag to',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='prefix',
            description='proxy tag prefix (e.g. {prefix}text)',
            max_length=50,
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='suffix',
            description='proxy tag suffix (e.g. text{suffix})',
            max_length=50,
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='regex',
            description='whether the proxy tag is matched with regex (default: False)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='case_sensitive',
            description='whether the proxy tag is case sensitive (default: False)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_proxy_tags_add(
    interaction: Interaction,
    member: ProxyMember,
    prefix: str | None = None,
    suffix: str | None = None,
    regex: bool = False,
    case_sensitive: bool = False
) -> None:
    if len(member.proxy_tags) >= 15:
        raise InteractionError('members can only have 15 proxy tags')

    member.proxy_tags.append(
        ProxyTag(
            prefix=prefix or '',
            suffix=suffix or '',
            regex=regex,
            case_sensitive=case_sensitive
        )
    )

    await gather(
        member.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'added proxy tag to member `{member.name}`'
            )]
        )
    )


@member_proxy_tags.command(
    name='list',
    description='list a member\'s proxy tags',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to list tags of',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_proxy_tags_list(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    await interaction.response.send_message(
        embeds=[Embed.success(
            title=f'proxy tags for member {member.name}',
            message='\n'.join([
                ':'.join([
                    f'`{index}`',
                    f'{'r' if tag.regex else ''}{'c' if tag.case_sensitive else ''}'
                    f' {tag.prefix}text{tag.suffix}'])
                for index, tag in enumerate(member.proxy_tags)
            ]) or 'this member has no proxy tags'
        )]
    )


@member_proxy_tags.command(
    name='remove',
    description='remove a proxy tag from a member',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to remove tag from',
            required=True),
        ApplicationCommandOption(  # ! make an autocomplete for this {prefix}text{suffix}
            type=ApplicationCommandOptionType.INTEGER,
            name='index',
            min_value=0,
            max_value=14,
            description='index of the tag to remove (use /member proxy_tags list to get the index)',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_proxy_tags_remove(
    interaction: Interaction,
    member: ProxyMember,
    index: int
) -> None:
    if index < 0 or index >= len(member.proxy_tags):
        raise InteractionError('proxy tag index out of range')

    member.proxy_tags.pop(index)

    await gather(
        member.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'removed proxy tag from member `{member.name}`'
            )]
        )
    )


@member_proxy_tags.command(
    name='clear',
    description='clear all proxy tags from a member',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to clear tags from',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_proxy_tags_clear(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    member.proxy_tags.clear()

    await gather(
        member.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'cleared proxy tags from member `{member.name}`'
            )]
        )
    )


@member_userproxy.command(
    name='new',
    description='create a new userproxy (see /help)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to create userproxy for',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='bot_token',
            description='bot token to use for userproxy',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_command',
            description='command to use when proxying (default: /proxy)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='store_token',
            description='whether to store bot token, required for some features (see /help) (default: True)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_new(
    interaction: Interaction,
    member: ProxyMember,
    bot_token: str,
    proxy_command: str = '/proxy',
    store_token: bool = True
) -> None:
    ...


@member_userproxy.command(
    name='sync',
    description='sync member with userproxy, generally not required unless bot token is not stored',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to sync',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='bot_token',
            description='bot token to use to sync userproxy (required if bot token is not stored)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_sync(
    interaction: Interaction,
    member: ProxyMember,
    bot_token: str | None = None
) -> None:
    ...


@member_userproxy.command(
    name='edit',
    description='edit a userproxy',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to edit userproxy for',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_command',
            description='update the command to use when proxying',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='bot_token',
            description='store the bot token, required for some features (see /help)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_edit(
    interaction: Interaction,
    member: ProxyMember,
    proxy_command: str | None = None,
    bot_token: str | None = None
) -> None:
    ...


@member_userproxy.command(
    name='remove',
    description='remove a userproxy (DOES NOT DELETE THE MEMBER OR BOT)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to remove userproxy from',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_remove(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    ...
