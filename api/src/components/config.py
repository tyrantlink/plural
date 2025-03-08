from collections.abc import Callable
from dataclasses import dataclass
from textwrap import dedent
from asyncio import gather
from typing import Any
from enum import Enum

from plural.db import Usergroup, Guild, Group, ProxyMember
from plural.db.enums import ReplyFormat, PaginationStyle
from plural.missing import MISSING
from plural.otel import span

from src.discord import (
    insert_cmd_ref,
    string_select,
    ButtonStyle,
    Interaction,
    ChannelType,
    Permission,
    SelectMenu,
    ActionRow,
    button,
    Embed,
    Emoji
)

from .pagination import PAGINATION_STYLE_MAP
from .base import _send_or_update


__all__ = (
    'PAGES',
)


class ConfigOptionType(Enum):
    BOOLEAN = 0
    SELECT = 1
    CHANNEL = 2


@dataclass
class ConfigOption:
    name: str
    description: str
    type: ConfigOptionType
    choices: list[SelectMenu.Option] | None = None
    docs: str | None = None
    parser: Callable[[str], Any] | None = None
    channel_types: list[ChannelType] | None = None


CONFIG_OPTIONS = CONFIG_OPTIONS = {
    'user': {
        'reply_format': ConfigOption(
            name='Reply Format',
            description=dedent('''
                The format for message references using webhooks.

                - None: No embedded reply, replies will only be part of the command.
                    - Note that these replies will not be visible to mobile users

                - Inline: Reply will be at the top of your message.
                    - This is the default behavior

                - Embed: Reply will be in an Embed
                    - This is the most visible option, but takes up more space and replies will be at the bottom of your message
            ''').strip(),
            type=ConfigOptionType.SELECT,
            choices=[
                SelectMenu.Option(
                    label='None',
                    value='0',
                    description='No embedded reply'),
                SelectMenu.Option(
                    label='Inline',
                    value='1',
                    description='Reply will be at the top of your message'),
                SelectMenu.Option(
                    label='Embed',
                    value='2',
                    description='Reply will be in an Embed')],
            parser=lambda value: ReplyFormat(int(value))),
        'groups_in_autocomplete': ConfigOption(
            name='Groups in Autocomplete',
            description=dedent('''
                Whether to show group name in member autocomplete.

                Note: group will always be hidden if you only have a single group.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'pagination_style': ConfigOption(
            name='Pagination Button Style',
            description=dedent('''
                The style of pagination buttons to use.

                Change the style of left and right buttons when viewing lists.

                For example, {cmd_ref[member list]} and {cmd_ref[group list]}.
            ''').strip(),
            type=ConfigOptionType.SELECT,
            choices=[
                SelectMenu.Option(
                    label='Basic Arrows',
                    value='0',
                    description='Simple left and right arrow emojis'),
                SelectMenu.Option(
                    label='Text Arrows',
                    value='1',
                    description='Simple left and right arrow text'),
                SelectMenu.Option(
                    label='Rem and Ram',
                    value='2',
                    description='Rem and Ram from Re:Zero')],
            parser=lambda value: PaginationStyle(int(value)))},
    'userproxy': {
        'reply_format': ConfigOption(
            name='Server Reply Format',
            description=dedent('''
                The format for message references in servers.

                - None: No embedded reply, replies will only be part of the command.
                    - Note that these replies will not be visible to mobile users

                - Inline: Reply will be at the top of your message.
                    - This is the default behavior

                - Embed: Reply will be in an Embed
                    - This is the most visible option, but takes up more space and replies will be at the bottom of your message
            ''').strip(),
            type=ConfigOptionType.SELECT,
            choices=[
                SelectMenu.Option(
                    label='None',
                    value='0',
                    description='No embedded reply'),
                SelectMenu.Option(
                    label='Inline',
                    value='1',
                    description='Reply will be at the top of your message'),
                SelectMenu.Option(
                    label='Embed',
                    value='2',
                    description='Reply will be in an Embed')],
            parser=lambda value: ReplyFormat(int(value))),
        'dm_reply_format': ConfigOption(
            name='DM Reply Format',
            description=dedent('''
                The format for message references in DMs.

                - None: No embedded reply, replies will only be part of the command.
                    - Note that these replies will not be visible to mobile users

                - Inline: Reply will be at the top of your message.
                    - This is the default behavior

                - Embed: Reply will be in an Embed
                    - This is the most visible option, but takes up more space and replies will be at the bottom of your message
            ''').strip(),
            type=ConfigOptionType.SELECT,
            choices=[
                SelectMenu.Option(
                    label='None',
                    value='0',
                    description='No embedded reply'),
                SelectMenu.Option(
                    label='Inline',
                    value='1',
                    description='Reply will be at the top of your message'),
                SelectMenu.Option(
                    label='Embed',
                    value='2',
                    description='Reply will be in an Embed')],
            parser=lambda value: ReplyFormat(int(value))),
        'ping_replies': ConfigOption(
            name='Ping Replies',
            description=dedent('''
                Whether to ping when you reply to someone with a userproxy.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'include_group_tag': ConfigOption(
            name='Include Group Tag in Member Name',
            description=dedent('''
                Whether to include the group tag in the member name.

                Note: the total length of userproxy name and group tag must be less than 32 characters.

                You may need to restart your client to see changes.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'attachment_count': ConfigOption(
            name='Attachment Count',
            description=dedent('''
                The number of attachments options to include in the proxy command.

                Trade-off between being able to send more attachments and having more cluttered in the command.
            ''').strip(),
            type=ConfigOptionType.SELECT,
            choices=[
                SelectMenu.Option(
                    label=str(index),
                    value=str(index))
                for index in range(1, 11)],
            parser=lambda value: int(value)),
        'self_hosted': ConfigOption(
            name='Self Hosted',
            description=dedent('''
                Whether your userproxies are self-hosted.

                Note: the self hosting client is currently in development. Using this option right now will break your userproxies.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'required_message_parameter': ConfigOption(
            name='Required Message Parameter',
            description=dedent('''
                Whether the proxy command requires the message parameter.

                If enabled, you must always have some message content, even if you include attachments.

                If disabled, you will have to manually select the message parameter, which can make the command harder to use, especially on mobile.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'name_in_reply_command': ConfigOption(
            name='Name in Reply Command',
            description=dedent('''
                Whether the userproxy name should be included in the reply command.

                If enabled, the reply command will be "Reply (userproxy name)"

                If disabled, the reply command will be "Reply"

                Either way, the userproxy icon will will be visible in the command.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled')},
    'guild': {
        'logclean': ConfigOption(
            name='Log Clean',
            description=dedent('''
                Whether to clean up log messages.

                If enabled, deleted message logs from compatible bots will be automatically deleted.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'log_channel': ConfigOption(  # ! do a channel select
            name='Log Channel',
            description=dedent('''
                The channel to send log messages to.

                If set, proxy logs will be sent to this channel.
            ''').strip(),
            type=ConfigOptionType.CHANNEL,
            channel_types=[ChannelType.GUILD_TEXT],
        )
    }
}


PAGES = {
    'home': lambda interaction: _home(
        interaction),
    'category': lambda interaction, category: _category(
        interaction, category),
    'option': lambda interaction, selected, category: _option(
        interaction, selected, category)
}


def extract_values(config: dict) -> dict[str, tuple[str, Any]]:
    out = {}

    for key, value in config.items():
        match value:
            case Enum():
                out[key] = (
                    ' '.join([(
                        part.capitalize()
                        if part.lower() not in {'and', 'or'} else
                        part.lower())
                        for part in value.name.split('_')]),
                    value)
            case bool():
                out[key] = ('Enabled' if value else 'Disabled', value)
            case _:
                out[key] = (str(value), value)

    return out


@string_select(
    custom_id='select_config_category',
    options=[],
    placeholder='Select a category')
async def select_config_category(
    interaction: Interaction,
    selected: list[str]
) -> None:
    await PAGES['category'](interaction, selected[0])


@string_select(
    custom_id='select_config_option',
    options=[],  # ? this should be overwritten
    placeholder='Select an option')
async def select_config_option(
    interaction: Interaction,
    selected: list[str],
    category: str
) -> None:
    await PAGES['option'](interaction, selected, category)


@string_select(
    custom_id='select_config_value',
    options=[],
    placeholder='this should be overwritten')
async def select_config_value(
    interaction: Interaction,
    selected: list[str],
    category: str,
    option: str
) -> None:
    option_data = CONFIG_OPTIONS[category][option]

    value = option_data.parser(selected[0])

    match category:
        case 'user':
            parent = await Usergroup.get_by_user(interaction.author_id)
            config = parent.config
        case 'userproxy':
            parent = await Usergroup.get_by_user(interaction.author_id)
            config = parent.userproxy_config
        case 'guild':
            parent = await Guild.get(interaction.guild_id) or Guild(
                id=interaction.guild_id)
            config = parent.config
        case _:
            raise ValueError(f'Invalid category: {category}')

    setattr(config, option, value)

    await parent.save()

    if category == 'userproxy':
        await userproxy_sync(
            interaction,
            option,
            parent
        )

    await _option(interaction, [option], category)


@button(
    custom_id='button_back',
    label='<-',
    style=ButtonStyle.SECONDARY)
async def button_back(
    interaction: Interaction,
    page: str,
    *args  # noqa: ANN002
) -> None:
    await PAGES[page](interaction, *args)


@button(
    custom_id='button_true',
    label='true',
    style=ButtonStyle.SECONDARY)
async def button_true(
    interaction: Interaction,
    category: str,
    option: str
) -> None:
    await _button_bool(interaction, category, option, True)


@button(
    custom_id='button_false',
    label='false',
    style=ButtonStyle.SECONDARY)
async def button_false(
    interaction: Interaction,
    category: str,
    option: str
) -> None:
    await _button_bool(interaction, category, option, False)


async def _button_bool(
    interaction: Interaction,
    category: str,
    option: str,
    value: bool
) -> None:
    match category:
        case 'user':
            parent = await Usergroup.get_by_user(interaction.author_id)
            config = parent.config
        case 'userproxy':
            parent = await Usergroup.get_by_user(interaction.author_id)
            config = parent.userproxy_config
        case 'guild':
            parent = await Guild.get(interaction.guild_id) or Guild(
                id=interaction.guild_id)
            config = parent.config
        case _:
            raise ValueError(f'Invalid category: {category}')

    setattr(config, option, value)

    await parent.save()

    if category == 'userproxy':
        await userproxy_sync(
            interaction,
            option,
            parent
        )

    await _option(interaction, [option], category)


async def _home(
    interaction: Interaction
) -> None:
    embed = Embed(
        title='config',
        description='select a category',
        color=0x69ff69
    )

    options = [
        SelectMenu.Option(
            label='User Config',
            value='user',
            description='Configure this account\'s settings'),
        SelectMenu.Option(
            label='Userproxy Config',
            value='userproxy',
            description='Configure userproxy settings')
    ]

    if (
        interaction.member and
        interaction.member.permissions & Permission.MANAGE_GUILD
    ):
        options.append(SelectMenu.Option(
            label='Server Config',
            value='guild',
            description='Configure this server\'s settings'
        ))

    components = [ActionRow(components=[
        select_config_category.with_overrides(
            options=options
        )])
    ]

    await _send_or_update(interaction, embed, components)


async def _category(
    interaction: Interaction,
    category: str
) -> None:
    usergroup = await Usergroup.get_by_user(interaction.author_id)

    match category:
        case 'user' | 'userproxy':
            userproxy = category == 'userproxy'

            embed = Embed(
                title=f'User{'proxy' if userproxy else ''} Config',
                color=0x69ff69
            ).set_author(
                name=interaction.author.display_name,
                icon_url=interaction.author.avatar_url
            )

            config = (
                usergroup.userproxy_config
                if userproxy else
                usergroup.config
            )

        case 'guild':
            guild = await Guild.get(interaction.guild_id) or Guild(
                id=interaction.guild_id
            )

            embed = Embed(
                title='Server Config',
                color=0x69ff69
            ).set_author(
                name=interaction.guild.name,
                icon_url=interaction.guild.icon_url or MISSING
            )

            config = guild.config

    current_values = extract_values(
        config.model_dump()
    )

    for raw_name, option in CONFIG_OPTIONS[category].items():
        embed.add_field(
            name=option.name,
            value=current_values.get(raw_name, ('Not Set',))[0],
            inline=False
        )

    components = [ActionRow(components=[
        select_config_option.with_overrides(
            options=[
                SelectMenu.Option(
                    label=option.name,
                    value=value)
                for value, option in CONFIG_OPTIONS[category].items()],
            placeholder='Select an option',
            extra=[category]
        )
    ])]

    arrow = PAGINATION_STYLE_MAP[
        usergroup.config.pagination_style
    ][0]

    components.append(ActionRow(components=[
        button_back.with_overrides(
            label=arrow if isinstance(arrow, str) else '',
            emoji=arrow if isinstance(arrow, Emoji) else None,
            extra=['home']
        )
    ]))

    await _send_or_update(interaction, embed, components)


async def _option(
    interaction: Interaction,
    selected: list[str],
    category: str
) -> None:
    option = CONFIG_OPTIONS[category][selected[0]]

    usergroup = await Usergroup.get_by_user(interaction.author_id)

    embed = Embed.success(
        title=option.name,
        message=option.description,
        insert_command_ref=True
    )

    match category:
        case 'user':
            config = usergroup.config
            embed.set_author(
                name=interaction.author.display_name,
                icon_url=interaction.author.avatar_url)
        case 'userproxy':
            config = usergroup.userproxy_config
            embed.set_author(
                name=interaction.author.display_name,
                icon_url=interaction.author.avatar_url)
        case 'guild':
            guild = await Guild.get(interaction.guild_id) or Guild(
                id=interaction.guild_id)
            config = guild.config
            embed.set_author(
                name=interaction.guild.name,
                icon_url=interaction.guild.icon_url or MISSING
            )

    current_values = extract_values(
        config.model_dump()
    )

    arrow = PAGINATION_STYLE_MAP[
        usergroup.config.pagination_style
    ][0]

    match option.type:
        case ConfigOptionType.BOOLEAN:
            components = [
                ActionRow(components=[
                    button_back.with_overrides(
                        label=arrow if isinstance(arrow, str) else '',
                        emoji=arrow if isinstance(arrow, Emoji) else None,
                        extra=['category', category]),
                    button_true.with_overrides(
                        style=(
                            ButtonStyle.SUCCESS
                            if current_values[selected[0]][1] else
                            ButtonStyle.SECONDARY),
                        extra=[category, selected[0]]),
                    button_false.with_overrides(
                        style=(
                            ButtonStyle.SUCCESS
                            if not current_values[selected[0]][1] else
                            ButtonStyle.SECONDARY),
                        extra=[category, selected[0]])])]
        case ConfigOptionType.SELECT:
            components = [
                ActionRow(components=[
                    select_config_value.with_overrides(
                        options=[
                            SelectMenu.Option(
                                label=option.label,
                                value=option.value,
                                description=(
                                    insert_cmd_ref(option.description)
                                    if option.description else MISSING),
                                default=option.label == current_values[selected[0]][0])
                            for option in option.choices],
                        placeholder=option.name,
                        extra=[category, selected[0]])]),
                ActionRow(components=[
                    button_back.with_overrides(
                        label=arrow if isinstance(arrow, str) else '',
                        emoji=arrow if isinstance(arrow, Emoji) else None,
                        extra=['category', category])])]
        case ConfigOptionType.CHANNEL:
            raise NotImplementedError

    await _send_or_update(interaction, embed, components)


async def userproxy_sync(
    interaction: Interaction,
    option: str,
    usergroup: Usergroup
) -> None:
    from src.commands.userproxy import _userproxy_sync

    patch_filter = set()

    match option:
        case 'include_group_tag':
            patch_filter.add('username')
        case 'attachment_count':
            patch_filter.add('commands')
        case 'self_hosted':
            patch_filter.update(
                'interactions_endpoint_url',
                'event_webhooks_url',
                'event_webhooks_types',
                'event_webhooks_status')
        case 'required_message_parameter':
            patch_filter.add('commands')
        case 'name_in_reply_command':
            patch_filter.add('commands')
        case _:
            return

    groups = await Group.find({
        'accounts': usergroup.id
    }).to_list()

    userproxies = {
        group: member
        for group in groups
        for member in await ProxyMember.find({
            '_id': {'$in': list(group.members)},
            'userproxy': {'$ne': None}
        }).to_list()
    }

    if not userproxies:
        return

    await interaction.response.update_message(
        embeds=[interaction.message.embeds[0].set_footer(
            text='Userproxy sync in progress...')],
        components=[
            ActionRow(
                components=[
                    component.with_overrides(
                        disabled=True)
                    for component in
                    action_row.components])
            for action_row in
            interaction.message.components
        ]
    )

    with span(f'bulk syncing {len(userproxies)} userproxies'):
        await gather(*(
            _userproxy_sync(
                interaction,
                userproxy,
                patch_filter,
                silent=True,
                usergroup=usergroup,
                group=group)
            for group, userproxy in userproxies.items()
        ))
