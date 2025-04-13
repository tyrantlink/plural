from textwrap import dedent

from src.discord import (
    ButtonStyle,
    Interaction,
    ActionRow,
    button,
    Embed
)


PAGES = {
    'selfhost': lambda interaction, token, action: _selfhost(interaction, token, action)
}


@button(
    custom_id='button_reset_selfhost_token',
    label='Reset Token',
    style=ButtonStyle.DANGER)
async def button_reset_selfhost_token(
    interaction: Interaction
) -> None:
    if interaction.message.components[0].components[0].label != 'Confirm':
        await PAGES['selfhost'](
            interaction,
            None,
            'reset'
        )
        return

    usergroup = await interaction.get_usergroup()

    token = await usergroup.update_token()

    await PAGES['selfhost'](
        interaction,
        token,
        None
    )


async def _selfhost(
    interaction: Interaction,
    token: str | None,
    action: str | None
) -> None:
    embed = Embed.success(
        title='Self-hosting Userproxies',
        message=dedent('''
        **NOTE: The self-hosting application is currently not available.**
        This command is just a placeholder for testing and the docs may not exist yet.

        There are two different "levels" of self-hosting userproxies:
        ​1. Partial self-hosting
        - You host the userproxies, which allows you to set their status
        - All commands are still run by /plu/ral, so even if your host goes down, your userproxies will still work
        ​2. Full self-hosting
        - You host the userproxies, which allows you to set their status
        - All commands are sent directly to your userproxies, they never reach /plu/ral servers.

        Level 2 allows for more privacy, but it isn't recommended unless you already have a server and can effectively guarantee uptime.

        Either way, if you'd like to self host, read the [self hosting documentation](https://plural.gg/guide/self-hosting) and then come back here when you're ready for your self hosting token.
        ''')
    )

    if token:
        embed.add_field(
            name='Token',
            value=f'||{token}||',
            inline=False
        )

    await interaction.response.send_message(
        embeds=[embed],
        components=[ActionRow(components=[button_reset_selfhost_token.with_overrides(
            label='Confirm' if action == 'reset' else 'Reset Token'
        )])]
    )
