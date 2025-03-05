from textwrap import dedent

from src.core.models import env

from src.discord import (
    ButtonStyle,
    Interaction,
    ActionRow,
    button,
    Embed
)

from .base import _send_or_update


__all__ = (
    'PAGES',
)


PAGES = {
    'help': lambda interaction, page: _help(interaction, page),
}

SUB_PAGES = {
    'main': f'Visit https://{env.domain} for detailed info, or click the buttons below for simple instructions',
    'getting started': dedent('''
        If you\'re coming from PluralKit or Tupperbox, start with the {cmd_ref[import]} command to use the proxies you already have.

        Otherwise, you can start by creating a new group with {cmd_ref[group new]},
          - If you don\'t create a group, a group named "default" will be created for you when you create a member.

        Create a new member with {cmd_ref[member new]}
          - all members *must* be a part of a group, specify in the {cmd_ref[member new]} command, or leave it blank to use the default group.

        Add some proxy tags with {cmd_ref[member tags add]}.

        Then, you can start proxying by using your set tags in a message, or enabling the autoproxy with {cmd_ref[autoproxy]}.

        That\'s all the basics, otherwise, simply type `/` and see what commands are available, or check out the [wiki](https://{env.domain}) for more info.
    ''').strip(),
    'userproxies': dedent(f'''
        Userproxies are proxy members attached to a real Discord Bot, giving them the ability to be used in DMs, Group DMs, and servers without /plu/ral. They can also have bios and banner images right in their pop out.

        This feature is advanced and requires a lot of setup, if you want to use it, [follow the instructions on the wiki](<https://{env.domain}/guide/userproxies#creating-a-userproxy>).
    ''').strip(),
    'info and support': dedent(f'''
        - for more information, check out the [wiki](https://{env.domain}),
        - for support, join the [discord](https://discord.gg/4mteVXBDW7),
        - for bugs, suggestions, or other feedback, open an issue on the github or post in the support channel
        - [privacy policy](<https://{env.domain}/privacy-policy>)
        - [terms of service](<https://{env.domain}/terms-of-service>)
        - [github](https://github.com/tyrantlink/plural)
    ''').strip(),
}


@button(
    custom_id='button_help_main',
    label='Main',
    style=ButtonStyle.PRIMARY)
async def button_help_main(
    interaction: Interaction
) -> None:
    await _help(interaction, 'main')


@button(
    custom_id='button_help_getting_started',
    label='Getting Started',
    style=ButtonStyle.SECONDARY)
async def button_help_getting_started(
    interaction: Interaction
) -> None:
    await _help(interaction, 'getting started')


@button(
    custom_id='button_help_userproxies',
    label='Userproxies',
    style=ButtonStyle.SECONDARY)
async def button_help_userproxies(
    interaction: Interaction
) -> None:
    await _help(interaction, 'userproxies')


@button(
    custom_id='button_help_info_and_support',
    label='Info and Support',
    style=ButtonStyle.SECONDARY)
async def button_help_info_and_support(
    interaction: Interaction
) -> None:
    await _help(interaction, 'info and support')


async def _help(
    interaction: Interaction,
    page: str
) -> None:
    await _send_or_update(
        interaction,
        embed=Embed.success(
            title='Welcome to /plu/ral!',
            message=SUB_PAGES[page],
            insert_command_ref=True),
        components=[
            ActionRow(
                components=[
                    help_button.with_overrides(
                        style=(
                            ButtonStyle.PRIMARY
                            if help_button.label.lower() == page
                            else ButtonStyle.SECONDARY
                        ),
                    ) for help_button in [
                        button_help_main,
                        button_help_getting_started,
                        button_help_userproxies,
                        button_help_info_and_support
                    ]
                ]
            )
        ]
    )
