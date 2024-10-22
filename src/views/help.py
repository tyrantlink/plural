from __future__ import annotations
from discord import ButtonStyle, Interaction, Embed
from discord.ui import Button
from src.helpers import View


PAGES = {
    'main': 'please select a category',
    'getting started': '\n'.join([
        '- if you\'re coming from pluralkit or tupperbox, use the `/import` command and use your proxies as you have been',
        '- otherwise, you can start by creating a new group with `/group new`',
        '  - if you don\'t create a group, a group named "default" will be created for you when you create a member',
        '- create a new member with `/member new`',
        '  - all members *must* be a part of a group, specify in the `/member new` command, or leave it blank to use the default group',
        '- add some proxy tags with `/member proxy add`',
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
        '- use the `/userproxy new` command and set the member and bot token',
        '- optionally, enable autosync to have all changes to the member automatically update the bot, please note that this requires storing the bot token, if you\'re not comfortable with this, don\'t enable autosync',
        '- you can always use /userproxy sync to manually sync the userproxy with the bot',
        '- after running `/userproxy new`, click on the install link and add the bot to your account',
        '- you should now have access to the command /proxy, and the message commands reply and edit in DMs and servers',
    ]),
    'info and support': '\n'.join([
        '- for more information, check out the [github](https://github.com/tyrantlink/plural)',
        '- for support, join the [discord](https://discord.gg/6t8V4Cv)',
        '- for bugs, suggestions, or other feedback, open an issue on the github or post in the support channel'])
}


class HelpButton(Button):
    def __init__(self, parent: HelpView, label: str, **kwargs):
        self.parent = parent
        super().__init__(
            label=label,
            **kwargs
        )

    async def callback(self, interaction: Interaction):
        assert self.label is not None
        self.parent.page = self.label.lower()
        self.parent.update()

        await interaction.response.edit_message(
            embed=self.parent.embed,
            view=self.parent
        )


class HelpView(View):
    def __init__(self, **kwargs):
        super().__init__(
            timeout=kwargs.pop('timeout', None),
            **kwargs)

        self.page = 'main'
        self.embed = Embed(
            title='welcome to /plu/ral!',
            color=0x69ff69)
        self.update()

    def _update_embed(self) -> None:
        self.embed.description = PAGES[self.page]

    def _update_buttons(self) -> None:
        self.clear_items()

        self.add_items(
            *(
                HelpButton(
                    self, label,
                    style=(
                        ButtonStyle.primary
                        if label == self.page
                        else ButtonStyle.secondary
                    )
                )
                for label in PAGES
            )
        )

    def update(self) -> None:
        self._update_embed()
        self._update_buttons()
