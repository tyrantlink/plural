from src.discord import ActionRow, Interaction, Message, ButtonStyle, Component, Embed, Button
from src.logic.proxy import get_proxy_webhook
from src.discord.components import button
from src.errors import InteractionError
from src.models import project
from functools import partial
from asyncio import gather
from copy import deepcopy

__all__ = ('help_components',)


PAGES = {
    'main': 'please select a category',
    'getting started': '\n'.join([
        '- if you\'re coming from pluralkit or tupperbox, use the `/import` command to use the proxies you already have',
        '- otherwise, you can start by creating a new group with `/group new`',
        '  - if you don\'t create a group, a group named "default" will be created for you when you create a member',
        '- create a new member with `/member new`',
        '  - all members *must* be a part of a group, specify in the `/member new` command, or leave it blank to use the default group',
        '- add some proxy tags with `/member tags add`',
        '- that\'s all the basics, otherwise, simply type `/` and see what commands are available!']),
    'userproxies': '\n'.join([
        'note that this is an advanced feature, and requires some setup',
        '- userproxies allow you to proxy with your members in DMs and servers without /plu/ral',
        '- to get started, make sure you have imported/created your members',
        '- go to the [discord developer portal](https://discord.com/developers/applications) and click "New Application" in the top right',
        '- give your application the name of your member, and click "Create"',
        '- go to the "Installation" tab, and make sure to uncheck "Guild Install" and set the Install Link to None',
        '- go to the "Bot" tab and uncheck "Public Bot"',
        '- then on that same page, click "Reset Token", enter your password or 2FA, and copy the token',
        '- use the `/member userproxy new` command and set the member and bot token',
        '- by default, your bot token is stored, this is to enable automatic syncing between the bot and member, if you don\'t want this, you can set `store_token` to False',
        '- you can always use /member userproxy sync to manually sync the userproxy with the bot',
        '- after running `/member userproxy new`, click on the install link and add the bot to your account',
        '- you should now have access to the command /proxy (or custom name), and the message command reply. both of which DMs and servers',
        '\n\nto be able to edit messages, you\'ll needs to add /plu/ral to your account (click my profile picture and then "Add App")',
        '- you can use this edit command on any userproxy message, as well as any webhook messages that have been proxied',
        '- this will also enable you to manage your proxies from anywhere, including DMs and servers without /plu/ral',]),
    'info and support': '\n'.join([
        '- for more information, check out the [github](https://github.com/tyrantlink/plural)',
        '- for support, join the [discord](https://discord.gg/4mteVXBDW7)',
        '- for bugs, suggestions, or other feedback, open an issue on the github or post in the support channel',
        f'- [privacy policy](<{project.base_url}/privacy-policy>)',
        f'- [terms of service](<{project.base_url}/terms-of-service>)'
    ])
}


help_embed = partial(
    Embed.success,
    title='welcome to /plu/ral!'
)


@button(
    custom_id='button_help_main',
    label='main',
    style=ButtonStyle.PRIMARY)
async def button_help_main(
    interaction: Interaction
) -> None:
    await interaction.response.update_message(
        embeds=[help_embed(message=PAGES['main'])],
        components=help_components_with_active('main')
    )


@button(
    custom_id='button_help_getting_started',
    label='getting started',
    style=ButtonStyle.SECONDARY)
async def button_help_getting_started(
    interaction: Interaction
) -> None:
    await interaction.response.update_message(
        embeds=[help_embed(message=PAGES['getting started'])],
        components=help_components_with_active('getting_started')
    )


@button(
    custom_id='button_help_userproxies',
    label='userproxies',
    style=ButtonStyle.SECONDARY)
async def button_help_userproxies(
    interaction: Interaction
) -> None:
    await interaction.response.update_message(
        embeds=[help_embed(message=PAGES['userproxies'])],
        components=help_components_with_active('userproxies')
    )


@button(
    custom_id='button_help_info_and_support',
    label='info and support',
    style=ButtonStyle.SECONDARY)
async def button_help_info_and_support(
    interaction: Interaction
) -> None:
    await interaction.response.update_message(
        embeds=[help_embed(message=PAGES['info and support'])],
        components=help_components_with_active('info_and_support')
    )


help_components: list[Component] = [
    ActionRow(components=[
        button_help_main,
        button_help_getting_started,
        button_help_userproxies,
        button_help_info_and_support
    ])
]


def help_components_with_active(active: str) -> list[Component]:
    components = deepcopy(help_components)
    for row in components:
        assert isinstance(row, ActionRow)
        for component in row.components:
            assert isinstance(component, Button)
            if component.custom_id == f'button_help_{active}':
                component.style = ButtonStyle.PRIMARY
            else:
                component.style = ButtonStyle.SECONDARY

    return components
