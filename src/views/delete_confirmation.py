from __future__ import annotations
from src.helpers import View, send_error, SuccessEmbed
from discord import ButtonStyle, Interaction, Button
from typing import TYPE_CHECKING
from discord.ui import button
from asyncio import gather

if TYPE_CHECKING:
    from src.client import Client


class DeleteConfirmation(View):
    def __init__(self, client: Client, **kwargs):
        super().__init__(
            timeout=kwargs.pop('timeout', None),
            **kwargs
        )
        self.client = client
        self.add_item(self.button_confirm)

    @button(
        label='confirm',
        style=ButtonStyle.red,
        custom_id='button_confirm')
    async def button_confirm(self, button: Button, interaction: Interaction):
        if interaction.user is None:
            await send_error(interaction, 'you do not exist')
            return  # ? mypy stupid

        groups = await self.client.db.groups(interaction.user.id)
        tasks = []

        for group in groups:
            members = await group.get_members()
            tasks.append(group.delete())
            for member in members:
                tasks.append(member.delete())
                if member.avatar:
                    if avatar := await self.client.db.image(member.avatar):
                        tasks.append(avatar.delete())

        tasks.append(
            self.client.db._client.latches.delete_many({'user': interaction.user.id}))

        tasks.append(
            self.client.db._client.messages.delete_many({'author_id': interaction.user.id}))

        await gather(*tasks)

        await interaction.edit(
            embed=SuccessEmbed(
                'all data successfully deleted'
            ),
            view=None
        )

        self.stop()
