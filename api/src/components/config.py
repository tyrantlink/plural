from collections.abc import Callable
from dataclasses import dataclass
from textwrap import dedent
from asyncio import gather
from typing import Any
from enum import Enum

from plural.db import Usergroup, Guild, Group, ProxyMember
from plural.db.enums import ReplyFormat, PaginationStyle
from plural.errors import InteractionError
from plural.missing import MISSING
from plural.otel import span

from src.core.models import USERPROXY_FOOTER
from src.discord import (
    insert_cmd_ref,
    TextInputStyle,
    string_select,
    ButtonStyle,
    Interaction,
    ChannelType,
    Permission,
    SelectMenu,
    ActionRow,
    TextInput,
    button,
    Embed,
    Emoji,
    modal
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
    STRING = 3


@dataclass
class ConfigOption:
    name: str
    description: str
    type: ConfigOptionType
    parser: Callable[[str], Any]
    choices: list[SelectMenu.Option] | None = None
    docs: str | None = None
    check: tuple[Callable[[Any], bool], str] | None = None
    channel_types: list[ChannelType] | None = None
    text_input: TextInput | None = None


CONFIG_OPTIONS = {
    'user': {
        'account_tag': ConfigOption(
            name='Account Tag',
            description=dedent('''
                The global account tag for this account.

                This will be overridden by group tags.
            ''').strip(),
            type=ConfigOptionType.STRING,
            text_input=TextInput(
                custom_id='value',
                label='Account Tag',
                style=TextInputStyle.SHORT,
                required=False,
                max_length=79),
            parser=lambda value: value),
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
            name='Button Style',
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
            parser=lambda value: PaginationStyle(int(value))),
        'roll_embed': ConfigOption(
            # ! add link to dice roll docs (once they exist)
            name='Dice Roll Embed',
            description=dedent('''
                Whether to send dice roll results in an embed when using a dice roll block (e.g. {{2d20 + 6}}).

                You will always see the total value of the roll in your original message, and the value of each roll in the debug log

                If enabled, you'll see the value of each roll in an embed.

                If disabled, you'll only see the total value inserted into your original message
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'tag_format': ConfigOption(
            name='Tag Format',
            description=dedent('''
                The format for account/group tags

                {tag} in your format will be replaced with your account/group tag.

                Default: {tag}
            ''').strip(),
            type=ConfigOptionType.STRING,
            text_input=TextInput(
                custom_id='value',
                label='Tag Format',
                style=TextInputStyle.SHORT,
                placeholder='{tag}'),
            parser=lambda value: value,
            check=(
                lambda value: '{tag}' in value,
                'Value must contain {tag}')),
        'pronoun_format': ConfigOption(
            name='Pronoun Format',
            description=dedent('''
                The format for pronouns in member names.

                {pronouns} in your format will be replaced with the member's pronouns.

                Default: ({pronouns})
            ''').strip(),
            type=ConfigOptionType.STRING,
            text_input=TextInput(
                custom_id='value',
                label='Pronoun Format',
                style=TextInputStyle.SHORT,
                placeholder='({pronouns})'),
            parser=lambda value: value,
            check=(
                lambda value: '{pronouns}' in value,
                'Value must contain {pronouns}')),
        'include_tag': ConfigOption(
            name='Include Tag in Member Name',
            description=dedent('''
                Whether to include the account/group tag in the member name.

                Note: the total length of member name, tag, and pronouns must be less than 80 characters.

                Server config can override this setting, always showing tags.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'include_pronouns': ConfigOption(
            name='Include Pronouns in Member Name',
            description=dedent('''
                Whether to include the pronouns in the member name.

                Note: the total length of member name, tag, and pronouns must be less than 80 characters.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'display_name_order': ConfigOption(
            name='Display Name Order',
            description=dedent('''
                The order of display name components.

                Default: Name, Tag, Pronouns
            ''').strip(),
            type=ConfigOptionType.SELECT,
            choices=[
                SelectMenu.Option(
                    label='Name, Tag, Pronouns',
                    value='0,1,2'),
                SelectMenu.Option(
                    label='Name, Pronouns, Tag',
                    value='0,2,1'),
                SelectMenu.Option(
                    label='Tag, Name, Pronouns',
                    value='1,0,2'),
                SelectMenu.Option(
                    label='Tag, Pronouns, Name',
                    value='1,2,0'),
                SelectMenu.Option(
                    label='Pronouns, Name, Tag',
                    value='2,0,1'),
                SelectMenu.Option(
                    label='Pronouns, Tag, Name',
                    value='2,1,0')],
            parser=lambda value: [
                int(index) for index in value.split(',')]),
        'private_member_info': ConfigOption(
            name='Private Member Info',
            description=dedent('''
                Whether to show member details in the proxy info command.

                If enabled, **anyone** will see the following information in the proxy info command:
                - Pronouns
                - Bio
                - Birthday
                - Color

                Note that since this requires the proxy info command, these values will only be visible when the member is *used*

                This is a global option, and will affect all members.

                Default: Disabled
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled')},
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

                Only supports the inline reply format.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'include_tag': ConfigOption(
            name='Include Tag in Member Name',
            description=dedent('''
                Whether to include the account/group tag in the member name.

                Note: the total length of userproxy name, tag, and pronouns must be less than 32 characters.
            ''').strip(),
            type=ConfigOptionType.BOOLEAN,
            parser=lambda value: value == 'Enabled'),
        'include_pronouns': ConfigOption(
            name='Include Pronouns in Member Name',
            description=dedent('''
                Whether to include the pronouns in the member name.

                Note: the total length of userproxy name, tag, and pronouns must be less than 32 characters.
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

                If enabled, you will lose the following features (Discord limitation):
                - You cannot send attachments without message content, there must be some text
                - You will no longer get the message pop-up when you leave everything blank, meaning you can no longer send messages with multiple lines

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
            parser=lambda value: value == 'Enabled'),
        'include_attribution': ConfigOption(
            name='Include Attribution',
            description=dedent(f'''
                Whether to include attribution at the end of bio.

                If enabled, Userproxy bios will end with{USERPROXY_FOOTER}
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
        'force_include_tag': ConfigOption(
            name='Force Include Tag',
            description=dedent('''
                Whether to force the account/group tag to be visible for all members used in this server.

                This does **NOT** apply to userproxies
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
            parser=lambda value: int(value)
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
            case list() if key == 'display_name_order':
                out[key] = (
                    ', '.join([
                        'Name',
                        'Tag',
                        'Pronouns'
                    ][index] for index in value),
                    value)
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

    if option_data.check and not option_data.check[0](value):
        raise InteractionError(
            'Invalid value\n\n'
            f'{option_data.check[1]}'
        )

    match category:
        case 'user':
            parent = await interaction.get_usergroup()
            config = parent.config
        case 'userproxy':
            parent = await interaction.get_usergroup()
            config = parent.userproxy_config
        case 'guild':
            parent = await Guild.get(interaction.guild_id) or Guild(
                id=interaction.guild_id)
            config = parent.config
        case _:
            raise ValueError(f'Invalid category: {category}')

    setattr(config, option, value)

    await parent.save()

    synced = False
    if category in {'user', 'userproxy'}:
        synced = await userproxy_sync(
            interaction,
            category,
            option,
            parent
        )

    await _option(interaction, [option], category, synced)


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
    label='Enabled',
    style=ButtonStyle.SECONDARY)
async def button_true(
    interaction: Interaction,
    category: str,
    option: str
) -> None:
    await _button_bool(interaction, category, option, True)


@button(
    custom_id='button_false',
    label='Disabled',
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
            parent = await interaction.get_usergroup()
            config = parent.config
        case 'userproxy':
            parent = await interaction.get_usergroup()
            config = parent.userproxy_config
        case 'guild':
            parent = await Guild.get(interaction.guild_id) or Guild(
                id=interaction.guild_id)
            config = parent.config
        case _:
            raise ValueError(f'Invalid category: {category}')

    setattr(config, option, value)

    await parent.save()

    synced = False
    if category in {'user', 'userproxy'}:
        synced = await userproxy_sync(
            interaction,
            category,
            option,
            parent
        )

    await _option(interaction, [option], category, synced)


@modal(
    custom_id='modal_set',
    title='Set',
    text_inputs=[])
async def modal_set(
    interaction: Interaction,
    category: str,
    option: str,
    value: str
) -> None:
    option_data = CONFIG_OPTIONS[category][option]

    if option_data.check and not option_data.check[0](value):
        raise InteractionError(
            'Invalid value\n\n'
            f'{option_data.check[1]}'
        )

    match category:
        case 'user':
            parent = await interaction.get_usergroup()
            config = parent.config
        case 'userproxy':
            parent = await interaction.get_usergroup()
            config = parent.userproxy_config
        case 'guild':
            parent = await Guild.get(interaction.guild_id) or Guild(
                id=interaction.guild_id)
            config = parent.config
        case _:
            raise ValueError(f'Invalid category: {category}')

    setattr(config, option, value)

    await parent.save()

    synced = False
    if category in {'user', 'userproxy'}:
        synced = await userproxy_sync(
            interaction,
            category,
            option,
            parent
        )

    await _option(interaction, [option], category, synced)


@button(
    custom_id='button_set',
    label='Set',
    style=ButtonStyle.PRIMARY)
async def button_set(
    interaction: Interaction,
    category: str,
    option: str
) -> None:
    match category:
        case 'user':
            parent = await interaction.get_usergroup()
            config = parent.config
        case 'userproxy':
            parent = await interaction.get_usergroup()
            config = parent.userproxy_config
        case 'guild':
            parent = await Guild.get(interaction.guild_id) or Guild(
                id=interaction.guild_id)
            config = parent.config
        case _:
            raise ValueError(f'Invalid category: {category}')

    await interaction.response.send_modal(
        modal_set.with_overrides(
            title=f'Set {CONFIG_OPTIONS[category][option].name}',
            text_inputs=[
                CONFIG_OPTIONS[category][option].text_input.with_overrides(
                    value=getattr(config, option))],
            extra=[category, option]
        )
    )


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
    usergroup = await interaction.get_usergroup()

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
                name=interaction.guild.name or 'Server Name Unknown',
                icon_url=interaction.guild.icon_url or MISSING
            )

            config = guild.config

    current_values = extract_values(
        config.model_dump()
    )

    for raw_name, option in CONFIG_OPTIONS[category].items():
        embed.add_field(
            name=option.name,
            value=current_values.get(raw_name, ('',))[0] or 'Not Set',
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
    category: str,
    add_sync_footer: bool = False
) -> None:
    option = CONFIG_OPTIONS[category][selected[0]]

    usergroup = await interaction.get_usergroup()

    embed = Embed.success(
        title=option.name,
        message=(
            option.description.format(username=interaction.author_name)
            if (category, selected[0]) == ('userproxy', 'include_attribution') else
            option.description),
        insert_command_ref=True
    )

    if add_sync_footer:
        embed.set_footer(
            text=(
                'You may need to restart your client '
                'to see changes to userproxies'
            )
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
                name=interaction.guild.name or 'Server Name Unknown',
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
        case ConfigOptionType.STRING:
            embed.add_field(
                name='Current Value',
                value=current_values[selected[0]][0] or 'Not Set',
                inline=False)
            components = [
                ActionRow(components=[
                    button_back.with_overrides(
                        label=arrow if isinstance(arrow, str) else '',
                        emoji=arrow if isinstance(arrow, Emoji) else None,
                        extra=['category', category]),
                    button_set.with_overrides(
                        extra=[category, selected[0]])])]
        case ConfigOptionType.CHANNEL:
            raise NotImplementedError

    await _send_or_update(interaction, embed, components)


async def userproxy_sync(
    interaction: Interaction,
    category: str,
    option: str,
    usergroup: Usergroup
) -> bool:
    from src.commands.userproxy import _userproxy_sync

    patch_filter = set()

    match category, option:
        case ('user', 'account_tag'):
            patch_filter.add('username')
        case ('user', 'tag_format'):
            if usergroup.userproxy_config.include_tag:
                patch_filter.add('username')
        case ('user', 'pronoun_format'):
            if usergroup.userproxy_config.include_pronouns:
                patch_filter.add('username')
        case ('user', 'display_name_order'):
            patch_filter.add('username')
        case ('userproxy', 'include_tag'):
            patch_filter.add('username')
        case ('userproxy', 'include_pronouns'):
            patch_filter.add('username')
        case ('userproxy', 'attachment_count'):
            patch_filter.add('commands')
        case ('userproxy', 'self_hosted'):
            patch_filter.update(
                'interactions_endpoint_url',
                'event_webhooks_url',
                'event_webhooks_types',
                'event_webhooks_status')
        case ('userproxy', 'required_message_parameter'):
            patch_filter.add('commands')
        case ('userproxy', 'name_in_reply_command'):
            patch_filter.add('commands')
        case ('userproxy', 'include_attribution'):
            patch_filter.add('description')
        case _:
            return False

    groups = await Group.find({
        'account': usergroup.id
    }).to_list()

    userproxies = {
        member: group
        for group in groups
        for member in await ProxyMember.find({
            '_id': {'$in': list(group.members)},
            'userproxy': {'$ne': None}
        }).to_list()
    }

    if not userproxies:
        return False

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
            for userproxy, group in userproxies.items()
        ))

    return True
