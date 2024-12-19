from src.discord import ActionRow, Interaction, ButtonStyle, Component, Embed, Button
from src.discord.components import button
from src.models import project
from functools import partial
from copy import deepcopy

__all__ = (
    'help_components',
    'help_description'
)


PAGES = {
    'main': f'visit {project.base_url} for detailed info, or click the buttons below for simple instructions',
    'getting started': '\n'.join([
        '- if you\'re coming from pluralkit or tupperbox, use the `/import` command to use the proxies you already have',
        '- otherwise, you can start by creating a new group with `/group new`',
        '  - if you don\'t create a group, a group named "default" will be created for you when you create a member',
        '- create a new member with `/member new`',
        '  - all members *must* be a part of a group, specify in the `/member new` command, or leave it blank to use the default group',
        '- add some proxy tags with `/member tags add`',
        '- that\'s all the basics, otherwise, simply type `/` and see what commands are available!']),
    'userproxies': '\n\n'.join([
        'Userproxies are proxy members attached to a real Discord Bot, giving them the ability to be used in DMs, Group DMs, and servers without /plu/ral. They can also have bios and banner images right in their pop out.',
        f'This feature is advanced and requires a lot of setup, if you want to use it, [follow the instructions on the wiki](<{project.base_url}/guide/userproxies#creating-a-userproxy>).']),
    'info and support': '\n'.join([
        '- for more information, check out the [github](https://github.com/tyrantlink/plural)',
        '- for support, join the [discord](https://discord.gg/4mteVXBDW7)',
        '- for bugs, suggestions, or other feedback, open an issue on the github or post in the support channel',
        f'- [privacy policy](<{project.base_url}/privacy-policy>)',
        f'- [terms of service](<{project.base_url}/terms-of-service>)'
    ])
}

help_description = PAGES['main']


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
