from __future__ import annotations
from discord import ApplicationContext
from discord.ext.commands import Cog
from src.helpers import send_error
from typing import TYPE_CHECKING
from src.db import Group, Member


if TYPE_CHECKING:
    from src.client.base import ClientBase


class BaseCommands(Cog):
    def __init__(self, client: ClientBase):
        self.client = client

    async def _base_group_getter(self, interaction: ApplicationContext, group: str) -> Group | None:
        resolved_group = await self.client.db.group_by_name(interaction.author.id, group)

        if resolved_group is None:
            if group == 'default':
                resolved_group = self.client.db.new.group('default')
                resolved_group.accounts.add(interaction.author.id)
                await resolved_group.save()
                return resolved_group

            await send_error(interaction, f'group `{group}` not found')
            return None

        return resolved_group

    async def _base_member_getter(
        self,
        interaction: ApplicationContext,
        group: str,
        member: str
    ) -> tuple[Group, Member] | tuple[None, None]:
        resolved_group = await self._base_group_getter(interaction, group)

        if resolved_group is None:
            return None, None

        resolved_member = await resolved_group.get_member_by_name(member)

        if resolved_member is None:
            await send_error(interaction, f'member `{member}` not found')
            return None, None

        return resolved_group, resolved_member
