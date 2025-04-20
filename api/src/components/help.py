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

        Nearly everything is configurable via {cmd_ref[config]}, including both user and server settings.

        That\'s all the basics, otherwise, simply type `/` and see what commands are available, or check out the [wiki](https://{env.domain}) for more info.
    ''').strip(),
    'userproxies': dedent(f'''
        Userproxies are proxy members attached to a real Discord Bot, giving them the ability to be used in DMs, Group DMs, and servers without /plu/ral. They can also have bios and banner images right in their pop out.

        This feature is advanced and requires a lot of setup, if you want to use it, [follow the instructions on the wiki](<https://{env.domain}/guide/userproxies#creating-a-userproxy>).

        If you have a large number of members, you don't have to create a userproxy for each one, just the most frequently used, then you can use the {{cmd_ref[say]}} command to send messages as any member.

        The {{cmd_ref[say]}} responds with an embed, and does not support many of the features of a normal message, basically just text. Userproxies should always be used if you're willing to go through the setup.

        **Note: it is currently not possible to autoproxy with userproxies**, you must use the command every time.
        This may change in the future through client modding.
    ''').strip(),
    'info and support': dedent(f'''
        - for more information, check out the [wiki](https://{env.domain}),
        - for support, join the [discord](https://discord.gg/4mteVXBDW7),
        - for bugs, suggestions, or other feedback, open an issue on the github or post in the support channel
        - [privacy policy](<https://{env.domain}/privacy-policy>)
        - [terms of service](<https://{env.domain}/terms-of-service>)
        - [github](https://github.com/tyrantlink/plural)
    ''').strip(),
    'donate': dedent('''
        If you want to support the project, you can donate to help with server costs, and development.

        Benefits:
        - Less money in your bank account
        - 🌟/plu/ral supporter🌟 text on your proxy info page
        - The supporter role in [the support server](https://discord.gg/4mteVXBDW7)

        I don't plan on charging for features, and donation is permanent, even if you only donate $1, one time, you will keep your supporter status forever.

        I *may* add an increased avatar limit as a benefit in the future, since that has a direct cost to me
        (see {cmd_ref[stats]} for current usage/limit)

        Feel free to donate through whichever source you prefer, all donations are appreciated. Only Patreon and Discord rewards are automatic, the others require manual verification.

        - [Patreon](https://patreon.com/tyrantlink)
        - [Ko-fi](https://ko-fi.com/tyrantlink)\\*
        - [LiberaPay](https://liberapay.com/tyrantlink)\\*
        - [GitHub Sponsors](https://github.com/sponsors/tyrantlink)\\*
        - [Discord](https://discord.com/application-directory/1291501048493768784/store)\\*\\*
    ''').strip()
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


@button(
    custom_id='button_help_donate',
    label='Donate',
    style=ButtonStyle.SECONDARY)
async def button_help_donate(
    interaction: Interaction
) -> None:
    await _help(interaction, 'donate')


async def _help(
    interaction: Interaction,
    page: str
) -> None:
    embed = Embed.success(
        title='Welcome to /plu/ral!',
        message=SUB_PAGES[page],
        insert_command_ref=True
    )

    # ? make this more dynamic if more options are added
    if page == 'donate':
        embed.set_footer(
            text=(
                '* Rewards are not automatic, please contact the developer after you donate\n'
                '** Discord takes a 15% cut, so the other options are preferred'
            )
        )

    await _send_or_update(
        interaction,
        embed=embed,
        components=[
            ActionRow(components=[
                help_button.with_overrides(
                    style=(
                        ButtonStyle.PRIMARY
                        if help_button.label.lower() == page
                        else ButtonStyle.SECONDARY),
                ) for help_button in [
                    button_help_main,
                    button_help_getting_started,
                    button_help_userproxies,
                    button_help_info_and_support]]),
            ActionRow(components=[
                help_button.with_overrides(
                    style=(
                        ButtonStyle.PRIMARY
                        if help_button.label.lower() == page
                        else ButtonStyle.SECONDARY),
                ) for help_button in [
                    button_help_donate,
                ]
            ])
        ]
    )
