from src.discord import Interaction, InteractionContextType, ApplicationCommandOption, ApplicationCommandOptionType, Embed, ApplicationIntegrationType, Attachment, SlashCommandGroup, User, Application, COMMAND_NAME_PATTERN
from src.errors import InteractionError, Unauthorized, Forbidden, NotFound
from src.discord.commands import sync_commands, _put_all_commands
from src.models import USERPROXY_FOOTER, USERPROXY_FOOTER_LIMIT
from src.db import ProxyMember, Group, ImageExtension
from src.components import modal_plural_member_bio
from src.discord.http import _get_bot_id
from regex import match, UNICODE
from src.models import project
from asyncio import gather


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

member_tags = member.create_subgroup(
    name='tags',
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
            required=False,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_new(
    interaction: Interaction,
    name: str,
    group: Group | None = None
) -> None:
    group = group or await Group.get_or_create_default(interaction.author_id)

    if await group.get_member_by_name(name) is not None:
        raise InteractionError(
            f'member `{name}` already exists in group `{group.name}`')

    embeds = [
        Embed.success(f'member `{name}` created in group `{group.name}`')
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
            required=False,
            autocomplete=True)],
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
                    (
                        member.name
                        if member.userproxy is None else
                        f'[{member.name}](https://discord.com/oauth2/authorize?client_id={
                            member.userproxy.bot_id}&integration_type=1&scope=applications.commands)'
                    )
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
            required=True,
            autocomplete=True)],
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
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='name',
            description='new member name',
            max_length=80,
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_name(
    interaction: Interaction,
    member: ProxyMember,
    name: str
) -> None:
    if member.userproxy is not None and len(name) > 32:
        raise InteractionError(
            'members with userproxies must have names less than 32 characters')

    old_name, member.name = member.name, name

    group = await member.get_group()

    await gather(
        member.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'member `{old_name}` of group `{
                    group.name}` was renamed to `{name}`'
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
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='group',
            description='group name',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_group(
    interaction: Interaction,
    member: ProxyMember,
    group: Group
) -> None:
    if await group.get_member_by_name(member.name) is not None:
        raise InteractionError(
            f'group `{group.name}` already has a member named `{member.name}`')

    old_group = await member.get_group()

    old_group.members.remove(member.id)
    group.members.add(member.id)

    await gather(
        old_group.save(),
        group.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'member `{member.name}` of group `{
                    old_group.name}` was moved from group `{group.name}`'
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
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='avatar',
            description='new member avatar (max 10MB)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_avatar(
    interaction: Interaction,
    member: ProxyMember,
    avatar: Attachment | None = None
) -> None:
    if avatar is None:
        await gather(
            member.delete_avatar(),
            interaction.response.send_message(
                embeds=[Embed.success(
                    f'removed member `{member.name}` avatar'
                )]
            )
        )
        return

    if avatar.size > 10_485_760:
        raise InteractionError('avatars must be less than 10MB')

    if (
        '.' in avatar.filename and
        avatar.filename.rsplit(
            '.', 1)[-1].lower() not in {'png', 'jpeg', 'jpg', 'gif', 'webp'}
    ):
        raise InteractionError('avatars must be a png, jpg, gif, or webp')

    await interaction.response.defer()

    await member.set_avatar(avatar.url)
    assert member.avatar is not None

    response = f'group `{member.name}` now has the avatar `{avatar.filename}`'

    if member.avatar.extension == ImageExtension.GIF:
        response += '\n\n**note:** gif avatars are not animated'

    await interaction.followup.send(
        embeds=[Embed.success(response)]
    )


@member_set.command(
    name='bio',
    description='set a member\'s bio (userproxies only)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            max_length=USERPROXY_FOOTER_LIMIT,
            description='member to give new bio',
            required=True,
            autocomplete=True),
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
    include_attribution: bool = True
) -> None:
    if member.userproxy is None:
        raise InteractionError(
            'you can only set a bio for a userproxy (see /help)')

    if member.userproxy.token is None:
        raise InteractionError(
            'your userproxy must have a bot token stored to set a bio')

    try:
        app = await Application.fetch_current(member.userproxy.token)
    except Unauthorized:
        raise InteractionError('invalid bot token')

    if app.id != member.userproxy.bot_id:
        raise InteractionError('invalid bot token')

    if app.bot is None:  # ? *probably* shouldn't happen
        raise InteractionError('bot not found')

    max_length = USERPROXY_FOOTER_LIMIT if include_attribution else 400

    current_bio = app.description.removesuffix(
        USERPROXY_FOOTER.format(username=interaction.author_name)
    ).strip()

    await interaction.response.send_modal(
        modal_plural_member_bio.with_title(
            f'set {app.bot.username}\'s bio'
        ).with_text_kwargs(
            0,
            value=current_bio,
            max_length=max_length
        ).with_extra(
            member,
            include_attribution
        )
    )


@member_set.command(
    name='banner',
    description='set a member\'s banner (userproxies only)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='member to give new banner',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='banner',
            description='new member banner (max 15MB)',
            required=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_banner(
    interaction: Interaction,
    member: ProxyMember,
    banner: Attachment
) -> None:
    if member.userproxy is None:
        raise InteractionError(
            'you can only set a banner for a userproxy (see /help)')

    if member.userproxy.token is None:
        raise InteractionError(
            'your userproxy must have a bot token stored to set a banner')

    if banner.size > 15_728_640:
        raise InteractionError('banners must be less than 15MB')

    if (
        '.' in banner.filename and
        banner.filename.rsplit(
            '.', 1)[-1].lower() not in {'png', 'jpeg', 'jpg', 'gif', 'webp'}
    ):
        raise InteractionError('banners must be a png, jpg, gif, or webp')

    try:
        user = await User.fetch('@me', token=member.userproxy.token)
    except Unauthorized:
        raise InteractionError('invalid bot token')

    await interaction.response.defer()

    await user.patch(
        token=member.userproxy.token,
        banner=await banner.read()
    )

    await interaction.followup.send(
        embeds=[Embed.success(
            f'banner set for userproxy `{member.name}`'
        )]
    )


@member_tags.command(
    name='add',
    description='add proxy tags to a member (15 max)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to add tag to',
            required=True,
            autocomplete=True),
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
async def slash_member_tags_add(
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
        ProxyMember.ProxyTag(
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


@member_tags.command(
    name='list',
    description='list a member\'s proxy tags',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to list tags of',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_tags_list(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    await interaction.response.send_message(
        embeds=[Embed.success(
            title=f'proxy tags for member {member.name}',
            message='\n'.join([
                ':'.join([
                    f'`{index}`',
                    f'{'r' if tag.regex else ''}{
                        'c' if tag.case_sensitive else ''}'
                    f' {tag.prefix}text{tag.suffix}'])
                for index, tag in enumerate(member.proxy_tags)
            ]) or 'this member has no proxy tags'
        )]
    )


@member_tags.command(
    name='remove',
    description='remove a proxy tag from a member',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to remove tag from',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_tag',
            description='proxy tag to remove',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_tags_remove(
    interaction: Interaction,
    member: ProxyMember,
    proxy_tag: str
) -> None:
    index = int(proxy_tag)
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


@member_tags.command(
    name='clear',
    description='clear all proxy tags from a member',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='member',
            description='member to clear tags from',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_tags_clear(
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
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='bot_token',
            description='bot token to use for userproxy',
            required=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_command',
            description='command to use when proxying (default: /proxy)',
            min_length=1,
            max_length=32,
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
    proxy_command: str = 'proxy',
    store_token: bool = True
) -> None:
    bot_id = _get_bot_id(bot_token)
    proxy_command = proxy_command.lstrip('/')

    if member.userproxy is not None:
        raise InteractionError(
            f'member `{member.name}` already has a userproxy; use `/member userproxy remove` to remove it')

    if len(member.name) > 32:
        raise InteractionError(
            'members with userproxies must have names less than or equal to 32 characters in length')

    if not match(COMMAND_NAME_PATTERN, proxy_command, UNICODE):
        raise InteractionError(
            'invalid proxy command\n\ncommands must be alphanumeric and may contain dashes and underscores')

    potential_member = await ProxyMember.find_one({
        'userproxy.bot_id': bot_id
    })

    if potential_member is not None:
        raise InteractionError(
            f'userproxy with bot <@{bot_id}> already exists for member `{potential_member.name}`')

    try:
        app = await Application.fetch_current(bot_token)
    except (Unauthorized, NotFound, Forbidden):
        raise InteractionError(
            '\n\n'.join([
                f'invalid bot token; may be expired',
                f'please go to the [discord developer portal](https://discord.com/developers/applications/{bot_id}/bot) to reset the token',
                'then, use `/member userproxy edit` to update the token, make sure to set `store_token` to True!'
            ])
        )

    if app.bot is None:
        raise InteractionError('bot not found')

    member.userproxy = ProxyMember.UserProxy(
        bot_id=bot_id,
        public_key=app.verify_key,
        token=bot_token if store_token else None,
        command=proxy_command
    )

    await member.save()

    avatar = None
    if not avatar and member.avatar is not None:
        avatar = await member.get_avatar()

    if not avatar and (group := await member.get_group()).avatar is not None:
        avatar = await group.get_avatar()

    app_patch: dict = {
        'interactions_endpoint_url': f'{project.api_url}/discord/interaction'
    }
    bot_patch: dict = {
        'username': member.name
    }

    if not app.description:
        app_patch['description'] = USERPROXY_FOOTER.format(
            username=interaction.author_name).strip()

    if avatar is not None:
        app_patch['icon'] = avatar
        bot_patch['avatar'] = avatar

    await gather(
        app.patch(
            bot_token,
            **app_patch),
        app.bot.patch(
            bot_token,
            **bot_patch),
        sync_commands(bot_token),
        interaction.response.send_message(
            embeds=[Embed.success('\n'.join([
                f'userproxy created for member `{member.name}`\n',
                '[add the bot to your account](https://discord.com/oauth2/authorize?client_id={bot_id}&integration_type=1&scope=applications.commands)'
            ]))]
        )
    )


@member_userproxy.command(
    name='sync',
    description='sync member with userproxy, generally not required unless bot token is not stored',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='member to sync',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='bot_token',
            description='bot token to use to sync userproxy (required if bot token is not stored)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_sync(
    interaction: Interaction,
    userproxy: ProxyMember,
    bot_token: str | None = None
) -> None:
    if userproxy.userproxy is None:
        raise InteractionError(
            f'member `{member.name}` does not have a userproxy')

    token = bot_token or userproxy.userproxy.token

    if token is None:
        raise InteractionError(
            f'bot token for userproxy `{userproxy.name}` is not stored; provide a bot token to sync the userproxy')

    try:
        app = await Application.fetch_current(token)
    except (Unauthorized, NotFound, Forbidden):
        bot_id = _get_bot_id(token)

        raise InteractionError(
            '\n\n'.join([
                f'invalid bot token; may be expired',
                f'please go to the [discord developer portal](https://discord.com/developers/applications/{bot_id}/bot) to reset the token',
                'then, use `/member userproxy edit` to update the token, make sure to set `store_token` to True!'
            ])
        )

    if app.bot is None:
        raise InteractionError('bot not found')

    avatar = None
    if not avatar and userproxy.avatar is not None:
        avatar = await userproxy.get_avatar()

    if not avatar and (group := await userproxy.get_group()).avatar is not None:
        avatar = await group.get_avatar()

    app_patch: dict = {
        'interactions_endpoint_url': f'{project.api_url}/discord/interaction'
    }
    bot_patch: dict = {
        'username': userproxy.name
    }

    if not app.description:
        app_patch['description'] = USERPROXY_FOOTER.format(
            username=interaction.author_name)

    if avatar is not None:
        app_patch['icon'] = avatar
        bot_patch['avatar'] = avatar

    await gather(
        app.patch(
            token,
            **app_patch),
        app.bot.patch(
            token,
            **bot_patch),
        sync_commands(token),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'synced userproxy for member `{userproxy.name}`'
            )]
        )
    )


@member_userproxy.command(
    name='edit',
    description='edit a userproxy',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='member to edit userproxy for',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='proxy_command',
            description='update the command to use when proxying',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='bot_token',
            description='required if bot token is not stored (if given with store_token=True, token will be updated)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='store_token',
            description='whether to store bot token, required for some features (see /help) (default: False)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_edit(
    interaction: Interaction,
    userproxy: ProxyMember,
    proxy_command: str | None = None,
    bot_token: str | None = None,
    store_token: bool = False
) -> None:
    if userproxy.userproxy is None:
        raise InteractionError(
            f'member `{member.name}` does not have a userproxy')

    if userproxy.userproxy.token is None and bot_token is None:
        raise InteractionError(
            f'bot token for userproxy `{userproxy.name}` is not stored; provide a bot token to update the userproxy')

    update_token = store_token and bot_token is not None

    if update_token:
        userproxy.userproxy.token = bot_token

    if proxy_command is None:
        await gather(
            userproxy.save(),
            interaction.response.send_message(
                embeds=[Embed.success(
                    f'updated userproxy token for member `{userproxy.name}`'
                )]
            )
        )
        return

    proxy_command = proxy_command.lstrip('/')

    if not match(COMMAND_NAME_PATTERN, proxy_command, UNICODE):
        raise InteractionError(
            'invalid proxy command\n\ncommands must be alphanumeric and may contain dashes and underscores')

    userproxy.userproxy.command = proxy_command

    await userproxy.save()

    assert userproxy.userproxy.token is not None

    await gather(
        sync_commands(userproxy.userproxy.token),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'updated userproxy command{
                    ' and token' if update_token else ''} for member `{userproxy.name}`'
            )]
        )
    )


@member_userproxy.command(
    name='remove',
    description='remove a userproxy (DOES NOT DELETE THE MEMBER OR BOT)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='member to remove userproxy from',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_remove(
    interaction: Interaction,
    userproxy: ProxyMember
) -> None:

    if userproxy.userproxy is None:
        raise InteractionError(
            f'member `{member.name}` does not have a userproxy')

    # ? try to clear commands if we have the token
    if userproxy.userproxy.token is not None:
        try:
            await Application.fetch_current(userproxy.userproxy.token)
            await _put_all_commands(userproxy.userproxy.token, {})
        except Unauthorized:
            pass

    userproxy.userproxy = None

    await gather(
        userproxy.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'removed userproxy from member `{member.name}`'
            )]
        )
    )
