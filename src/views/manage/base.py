from __future__ import annotations
from discord import ButtonStyle, Interaction, Button, Embed
from src.helpers import View, CustomModal
from src.models import ManageTargetType
from typing import TYPE_CHECKING
from src.db import Group, Member
from discord.ui import button

if TYPE_CHECKING:
    from src.client import Client, ClientBase


# ? only includes ClientBase to fix mypy error, will never actually be ClientBase
class BaseManageView(View):
    def __init__(self, client: Client | ClientBase, group: Group, member: Member | None, **kwargs):
        if TYPE_CHECKING and not isinstance(client, Client):
            raise ValueError('client must be an instance of Client')

        super().__init__(
            timeout=kwargs.pop('timeout', None),
            **kwargs
        )

        self.group = group
        self.target = member or group
        self.target_type = ManageTargetType.MEMBER if member else ManageTargetType.GROUP
        self.client = client

    async def __post_init__(self):
        await self._reload_embed()

    async def _reload_embed(self) -> None:
        self.embed = Embed(
            title=f'manage {self.target_type.name.lower()}',
            color=0x69ff69
        )

        self.embed.set_author(
            name=self.target.name,
            icon_url=await self.target.get_avatar_url()
        )

    @button(
        label='new',
        style=ButtonStyle.green,
        custom_id='button_new')
    async def button_new(self, button: Button, interaction: Interaction) -> None:
        ...
        # modal = CustomModal(
        #     title=f'new {self.target_type.name.lower()}',
