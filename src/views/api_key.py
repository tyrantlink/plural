from __future__ import annotations
from discord import ButtonStyle, Interaction, Button, Embed
from src.helpers import View, send_error, SuccessEmbed
from typing import TYPE_CHECKING
from discord.ui import button
from asyncio import gather

if TYPE_CHECKING:
    from src.client import Client, ClientBase


# ? only includes ClientBase to fix mypy error, will never actually be ClientBase
class ApiKeyView(View):
    def __init__(self, client: Client | ClientBase, **kwargs):
        if TYPE_CHECKING and not isinstance(client, Client):
            raise ValueError('client must be an instance of Client')

        super().__init__(
            timeout=kwargs.pop('timeout', None),
            **kwargs)

        self.client = client
        self.add_item(
            self.button_reset_token  # type: ignore # ? mypy doesn't like these
        )

        self.embed = SuccessEmbed(
            'i\'ll put something here eventually, for now it\'s just a token reset portal\nhttps://api.plural.gg/docs')
        self.embed.title = 'api key management'

    @button(
        label='reset token',
        style=ButtonStyle.red,
        custom_id='button_reset_token')
    async def button_reset_token(self, button: Button, interaction: Interaction):
        if interaction.user is None:
            await send_error(interaction, 'you do not exist')
            return  # ? mypy stupid

        api_key, token = self.client.db.new.api_key(interaction.user.id)

        embed = Embed(
            title='api token reset!',
            description='WARNING: this is the only time you will be able to see this token, make sure to save it somewhere safe!',
            color=0x69ff69)
        embed.add_field(name='token', value=f'`{token}`')

        await gather(
            api_key.save(),
            interaction.response.send_message(
                embed=embed,
                ephemeral=True
            ))
