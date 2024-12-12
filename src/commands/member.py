from src.discord import Interaction, InteractionContextType, ApplicationCommandOption, ApplicationCommandOptionType, Embed, ApplicationIntegrationType, Attachment, SlashCommandGroup, User, Application, Guild, COMMAND_NAME_PATTERN, EventType
from src.models import USERPROXY_FOOTER, USERPROXY_FOOTER_LIMIT, LEGACY_FOOTERS
from src.errors import InteractionError, Unauthorized, Forbidden, NotFound
from src.discord.commands import sync_commands, _put_all_commands
from src.db import ProxyMember, Group, ImageExtension
from src.components import modal_plural_member_bio
from src.models import project, MemberUpdateType
from src.discord.http import _get_bot_id
from regex import match, UNICODE
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


async def _self_hosted_warning(interaction: Interaction) -> None:
    await interaction.followup.send(
        embeds=[Embed.warning(
            title='self-hosted userproxy',
            message='you will need to host the userproxy yourself, see the [documentation](https://plural.gg/docs/userproxies/self-hosted) for more information'
        )]
    )


async def _sync_member_guilds(member: ProxyMember) -> None:
    if member.userproxy is None:
        raise ValueError('member does not have a userproxy')

    if member.userproxy.token is None:
        raise ValueError('member does not have a bot token stored')

    member.userproxy.guilds = [
        guild.id
        for guild in
        await Guild.fetch_user_guilds(
            member.userproxy.token
        )
    ]

    await member.save()


async def _userproxy_sync(
    member: ProxyMember,
    changes: set[MemberUpdateType],
    author_name: str,
    token: str | None = None
) -> Application:
    if member.userproxy is None:
        raise InteractionError(
            f'member `{member.name}` does not have a userproxy')

    bot_token = token or member.userproxy.token

    if bot_token is None:
        raise InteractionError(
            'bot token for userproxy `{member.name}` is not stored; provide a bot token to sync the userproxy')

    bot_id = _get_bot_id(bot_token)
    base_app_patch: dict = {
        'interactions_endpoint_url': f'{project.api_url}/discord/interaction' if not member.userproxy.self_hosted else None,
        'event_webhooks_url': f'{project.api_url}/discord/event',
        'event_webhooks_types': [EventType.APPLICATION_AUTHORIZED.value],
        'integration_types_config': {'0': {}, '1': {}},
        'install_params': None}
    app_patch: dict = {}
    bot_patch: dict = {}

    try:
        app = await Application.fetch_current(bot_token)
    except (Unauthorized, NotFound, Forbidden):
        raise InteractionError(
            '\n\n'.join([
                'invalid bot token; may be expired',
                f'please go to the [discord developer portal](https://discord.com/developers/applications/{bot_id}/bot) to reset the token',
                'then, use `/member userproxy edit` to update the token, make sure to set `store_token` to True!'
            ])
        ) from None

    if app.bot is None:
        raise InteractionError('bot not found')

    tasks = []

    for change in changes:
        match change:
            case MemberUpdateType.NAME:
                userproxy_name = (
                    (member.name + (f' {(await member.get_group()).tag}' or ''))
                    if member.userproxy.include_group_tag else
                    member.name
                )

                if len(userproxy_name) > 32:
                    raise InteractionError(
                        'members with userproxies must have names less than or equal to 32 characters in length (including group tag, if included)')

                bot_patch['username'] = userproxy_name
            case MemberUpdateType.AVATAR:
                avatar = None
                if member.avatar is not None:
                    avatar = await member.get_avatar()

                if not avatar and (group := await member.get_group()).avatar is not None:
                    avatar = await group.get_avatar()

                if avatar is not None:
                    app_patch['icon'] = avatar
                    bot_patch['avatar'] = avatar
            case MemberUpdateType.COMMAND:
                await sync_commands(member.userproxy.token)
            case MemberUpdateType.BIO:
                if not app.description:
                    app_patch['description'] = USERPROXY_FOOTER.format(
                        username=author_name)
            case MemberUpdateType.GUILDS:
                tasks.append(_sync_member_guilds(member))
            case _:
                continue

    tasks.extend([
        app.patch(bot_token, **base_app_patch),
        app.patch(bot_token, **app_patch),
        app.bot.patch(bot_token, **bot_patch)
    ])

    responses = await gather(*tasks, return_exceptions=True)

    for response in responses:
        if isinstance(response, Exception):
            raise InteractionError(
                'an error occurred while syncing the userproxy'
            ) from response

    return app


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

    if group.tag is not None and len(name+group.tag) > 79:
        embeds.append(Embed.warning('\n\n'.join([
            'member name with group tag is longer than 80 characters.',
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
            description='restrict to a single group',
            required=False,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_list(
    interaction: Interaction,
    group: Group | None = None
) -> None:
    groups = [group] if group is not None else await Group.find(
        {'accounts': interaction.author_id}).to_list()

    if not groups:
        await interaction.response.send_message(
            embeds=[Embed.success(
                title='members',
                message='you have no members'
            )])
        return

    group_padding = max(
        len(group.name)
        for group in groups
        if group.members
    ) + 3

    message = (
        '\n'.join([
            (
                member.name
                if member.userproxy is None else
                f'[{member.name}](https://discord.com/oauth2/authorize?client_id={member.userproxy.bot_id}&integration_type=1&scope=applications.commands)'
            )
            for member in await group.get_members()
        ])
        if group is not None else
        '\n'.join([  # ? discord strips duplicate spaces, so i have to do the stupid
            f'[{group.name}]'.ljust(group_padding).replace('  ', ' ​ ').replace('  ', ' ​ ') +
            (
                member.name
                if member.userproxy is None else
                f'[{member.name}](https://discord.com/oauth2/authorize?client_id={member.userproxy.bot_id}&integration_type=1&scope=applications.commands)'
            )
            for group in groups
            for member in await group.get_members()
        ])
    )

    pagination_required = False

    if len(message) > 4096:
        out = ''
        for line in message.split('\n'):
            if len(out) + len(line) > 4092:  # ? 4096 - 4 for '...'
                message = f'{out}\n...'
                pagination_required = True
                break

            out += line + '\n'

    embed = Embed.success(
        title=(
            f'members in group {group.name}'
            if group is not None else
            'members'),
        message=message or 'this group has no members'
    )

    if pagination_required:
        embed.set_footer(
            'character limit reached (pagination coming soon)')

    await interaction.response.send_message(embeds=[embed])


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


@member_set.command(
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
    group = await member.get_group()

    if member.userproxy is not None:
        userproxy_name = (
            name + (f' {(await member.get_group()).tag}' or '')
            if member.userproxy.include_group_tag else
            name)

        if len(userproxy_name) > 32:
            raise InteractionError(
                'members with userproxies must have names less than 32 characters (including group tag, if included)')

    old_name, member.name = member.name, name

    await gather(
        member.save(),
        _userproxy_sync(
            member,
            {MemberUpdateType.NAME},
            interaction.author_name),
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
                f'member `{member.name}` of group `{old_group.name}` was moved from group `{group.name}`'
            )]
        )
    )


@member_set.command(
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
            description='new member avatar (max 8MB)',
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

    if avatar.size > 8_388_608:
        raise InteractionError('avatars must be less than 8MB')

    if (
        '.' in avatar.filename and
        avatar.filename.rsplit(
            '.', 1)[-1].lower() not in {'png', 'jpeg', 'jpg', 'gif', 'webp'}
    ):
        raise InteractionError('avatars must be a png, jpg, gif, or webp')

    await interaction.response.defer()

    await member.set_avatar(avatar.url)
    assert member.avatar is not None

    response = f'member `{member.name}` of group `{(await member.get_group()).name}` now has the avatar `{avatar.filename}`'

    if member.avatar.extension == ImageExtension.GIF:
        response += '\n\n**note:** gif avatars are not animated (unless in a userproxy)'

    await interaction.followup.send(
        embeds=[Embed.success(response)]
    )

    if member.userproxy and member.userproxy.token:
        await _userproxy_sync(
            member,
            {MemberUpdateType.AVATAR},
            interaction.author_name
        )


@member_set.command(
    name='bio',
    description='set a member\'s bio (userproxies only)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            max_length=USERPROXY_FOOTER_LIMIT,
            description='member to give new bio (you\'ll type it in a prompt)',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='include_attribution',
            description='whether to add "a plural proxy for @user, powered by /plu/ral" to the end of the bio',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_set_bio(
    interaction: Interaction,
    userproxy: ProxyMember,
    include_attribution: bool = True
) -> None:
    if userproxy.userproxy is None:
        raise InteractionError(
            'you can only set a bio for a userproxy (see /help)')

    if userproxy.userproxy.token is None:
        raise InteractionError(
            'your userproxy must have a bot token stored to set a bio')

    try:
        app = await Application.fetch_current(userproxy.userproxy.token)
    except Unauthorized:
        raise InteractionError('invalid bot token') from None

    if app.id != userproxy.userproxy.bot_id:
        raise InteractionError('invalid bot token')

    if app.bot is None:  # ? *probably* shouldn't happen
        raise InteractionError('bot not found')

    max_length = USERPROXY_FOOTER_LIMIT if include_attribution else 400

    # ? attempt to strip legacy footer
    current_bio = app.description

    for footer in LEGACY_FOOTERS:
        current_bio = current_bio.removesuffix(
            footer.format(username=interaction.author_name)).strip()

    current_bio = current_bio.removesuffix(
        USERPROXY_FOOTER.format(username=interaction.author_name)[2:]
    ).strip()

    await interaction.response.send_modal(
        modal_plural_member_bio.with_title(
            f'set {app.bot.username}\'s bio'
        ).with_text_kwargs(
            0,
            value=current_bio[:max_length],  # ? truncate to max length
            max_length=max_length
        ).with_extra(
            userproxy,
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
    userproxy: ProxyMember,
    banner: Attachment
) -> None:
    if userproxy.userproxy is None:
        raise InteractionError(
            'you can only set a banner for a userproxy (see /help)')

    if userproxy.userproxy.token is None:
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
        user = await User.fetch('@me', token=userproxy.userproxy.token)
    except Unauthorized:
        raise InteractionError('invalid bot token') from None

    await interaction.response.defer()

    await user.patch(
        token=userproxy.userproxy.token,
        banner=await banner.read()
    )

    await interaction.followup.send(
        embeds=[Embed.success(
            f'banner set for userproxy `{userproxy.name}`'
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

    if prefix is None and suffix is None:
        raise InteractionError('at least one of prefix or suffix is required')

    proxy_tag = ProxyMember.ProxyTag(
        prefix=prefix or '',
        suffix=suffix or '',
        regex=regex,
        case_sensitive=case_sensitive
    )

    if proxy_tag in member.proxy_tags:
        raise InteractionError(f'member `{member.name}` already has this tag')

    existing_members: set[str] = set()
    async for group in Group.find({'accounts': interaction.author_id}):
        for existing_member in await group.get_members():
            if existing_member.id == member.id:
                continue

            for tag in existing_member.proxy_tags:
                if tag == proxy_tag:
                    existing_members.add(f'`[{group.name}] {member.name}`')

    member.proxy_tags.append(
        proxy_tag
    )

    await gather(
        member.save(),
        interaction.response.send_message(
            embeds=[Embed.success(
                f'added proxy tag to member `{member.name}`'
            )]
        )
    )

    if existing_members:
        await interaction.followup.send(
            embeds=[Embed.warning(
                title=f'tag overlaps with {len(existing_members)} other member{'s' if len(existing_members)-1 else ''}',
                message='\n'.join(existing_members)
            )]
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
            type=ApplicationCommandOptionType.BOOLEAN,
            name='store_token',
            description='whether to store bot token, required for some features (see /help) (default: True)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.INTEGER,
            name='attachment_count',
            min_value=0,
            max_value=10,
            description='number of attachment options to include on the proxy command (default: 1)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='include_group_tag',
            description='include group tag in userproxy name (default: False)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='self_hosted',
            description='whether your userproxy is self-hosted (default: False)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_new(
    interaction: Interaction,
    member: ProxyMember,
    bot_token: str,
    proxy_command: str = 'proxy',
    store_token: bool = True,
    attachment_count: int = 1,
    include_group_tag: bool = False,
    self_hosted: bool = False
) -> None:
    bot_id = _get_bot_id(bot_token)
    proxy_command = proxy_command.lstrip('/').lower()

    if member.userproxy is not None:
        raise InteractionError(
            f'member `{member.name}` already has a userproxy; use `/member userproxy remove` to remove it')

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
                'invalid bot token; may be expired',
                f'please go to the [discord developer portal](https://discord.com/developers/applications/{bot_id}/bot) to reset the token',
                'then, use `/member userproxy edit` to update the token, make sure to set `store_token` to True!'
            ])
        ) from None

    member.userproxy = ProxyMember.UserProxy(
        bot_id=bot_id,
        public_key=app.verify_key,
        token=bot_token if store_token else None,
        command=proxy_command,
        attachment_count=attachment_count,
        include_group_tag=include_group_tag,
        self_hosted=self_hosted
    )

    await member.save()

    await gather(
        _userproxy_sync(
            member,
            {MemberUpdateType.NAME, MemberUpdateType.AVATAR,
                MemberUpdateType.COMMAND, MemberUpdateType.GUILDS},
            interaction.author_name,
            bot_token),
        interaction.response.send_message(
            embeds=[Embed.success('\n\n'.join([
                f'userproxy created for member `{member.name}`',
                f'[add the bot to your account](https://discord.com/oauth2/authorize?client_id={bot_id}&integration_type=1&scope=applications.commands)',
                'note: you may need to restart discord for the commands to show up'
            ]))]
        )
    )

    if self_hosted:
        await _self_hosted_warning(interaction)


@member_userproxy.command(
    name='sync',
    description='sync member with userproxy, generally not required unless bot token is not stored or something broke',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='member to sync',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='sync_avatar',
            description='sync avatar (default: False)',
            required=False),
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
    sync_avatar: bool = False,
    bot_token: str | None = None
) -> None:
    changes = {
        MemberUpdateType.NAME,
        MemberUpdateType.COMMAND,
        MemberUpdateType.GUILDS
    }

    if sync_avatar:
        changes.add(MemberUpdateType.AVATAR)

    await interaction.response.defer()

    await _userproxy_sync(
        userproxy,
        changes,
        interaction.author_name,
        bot_token
    )

    await interaction.followup.send(
        embeds=[
            Embed.success(
                f'synced userproxy for member `{userproxy.name}`'
            )
        ]
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
            type=ApplicationCommandOptionType.BOOLEAN,
            name='store_token',
            description='whether to store bot token, required for some features (see /help) (default: False)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.INTEGER,
            name='attachment_count',
            min_value=0,
            max_value=10,
            description='number of attachment options to include on the proxy command (default: Unset)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='include_group_tag',
            description='include group tag in userproxy name (default: Unset)',
            required=False),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='self_hosted',
            description='whether your userproxy is self-hosted (default: Unset)',
            required=False)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_edit(
    interaction: Interaction,
    userproxy: ProxyMember,
    proxy_command: str | None = None,
    bot_token: str | None = None,
    store_token: bool = False,
    attachment_count: int | None = None,
    include_group_tag: bool | None = None,
    self_hosted: bool | None = None
) -> None:
    if userproxy.userproxy is None:
        raise InteractionError(
            f'member `{member.name}` does not have a userproxy')

    sync_changes = set()

    if proxy_command is not None:
        proxy_command = proxy_command.lstrip('/').lower()

        if not match(COMMAND_NAME_PATTERN, proxy_command, UNICODE):
            raise InteractionError(
                'invalid proxy command\n\ncommands must be lowercase alphanumeric and may contain dashes and underscores')

        userproxy.userproxy.command = proxy_command
        sync_changes.add(MemberUpdateType.COMMAND)

    if store_token and bot_token is not None:
        userproxy.userproxy.token = bot_token

    if attachment_count is not None:
        userproxy.userproxy.attachment_count = attachment_count
        sync_changes.add(MemberUpdateType.COMMAND)

    if include_group_tag is not None:
        userproxy.userproxy.include_group_tag = include_group_tag
        sync_changes.add(MemberUpdateType.NAME)

    if self_hosted is not None:
        userproxy.userproxy.self_hosted = self_hosted

    embed = Embed.success(
        f'updated userproxy for member `{userproxy.name}`'
    )

    if MemberUpdateType.COMMAND in sync_changes:
        embed.set_footer(
            'note: you may need to restart discord for the command changes to show up')

    tasks = [
        userproxy.save(),
        interaction.response.send_message(
            embeds=[embed]
        )
    ]

    if sync_changes:
        tasks.append(
            _userproxy_sync(
                userproxy,
                sync_changes,
                interaction.author_name,
                bot_token
            )
        )

    await gather(*tasks)

    if self_hosted is not None and self_hosted:
        await _self_hosted_warning(interaction)


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
            f'member `{userproxy.name}` does not have a userproxy')

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
                f'removed userproxy from member `{userproxy.name}`'
            )]
        )
    )


@member_userproxy.command(
    name='invite',
    description='invite a userproxy to a server',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='member to invite userproxy for',
            required=True,
            autocomplete=True)],
    contexts=InteractionContextType.ALL(),
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_invite(
    interaction: Interaction,
    userproxy: ProxyMember
) -> None:
    if userproxy.userproxy is None:
        raise InteractionError(
            f'member `{userproxy.name}` does not have a userproxy')

    await interaction.response.send_message(
        embeds=[Embed.success(
            title='invite userproxy',
            message='\n\n'.join([
                f'[add the bot to your account](https://discord.com/oauth2/authorize?client_id={userproxy.userproxy.bot_id}&integration_type=1&scope=applications.commands)',
                f'[invite the bot to a server](https://discord.com/oauth2/authorize?client_id={userproxy.userproxy.bot_id}&permissions=0&integration_type=0&scope=bot)'
            ])
        )]
    )


@member_userproxy.command(
    name='nickname',
    description='set a userproxy\'s nickname in this server (bot must be added to the server)',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='userproxy',
            description='member to set nickname for',
            required=True,
            autocomplete=True),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='nickname',
            description='new nickname (leave blank to remove)',
            required=False)],
    contexts=[InteractionContextType.GUILD],
    integration_types=ApplicationIntegrationType.ALL())
async def slash_member_userproxy_nickname(
    interaction: Interaction,
    userproxy: ProxyMember,
    nickname: str | None = None
) -> None:
    if userproxy.userproxy is None:
        raise InteractionError(
            f'member `{userproxy.name}` does not have a userproxy')

    if userproxy.userproxy.token is None:
        raise InteractionError(
            'your userproxy must have a bot token stored to set a nickname')

    if interaction.guild is None:
        raise InteractionError(
            'current server not found'
        )

    if interaction.guild.id not in userproxy.userproxy.guilds:
        raise InteractionError(
            'bot is not in this server; use `/member userproxy invite` to invite the bot and then use `/member userproxy sync` to sync the bot'
        )

    try:
        await interaction.guild.modify_current_member(
            nick=nickname,
            token=userproxy.userproxy.token
        )
    except NotFound:
        raise InteractionError(
            'bot is not in this server; use `/member userproxy invite` to invite the bot and then use `/member userproxy sync` to sync the bot'
        ) from None
    except Forbidden:
        raise InteractionError(
            'bot does not have permission to change it\'s own nickname'
        ) from None

    await interaction.response.send_message(
        embeds=[Embed.success(
            f'set nickname for userproxy `{userproxy.name}` to `{nickname}`'
        )]
    )
