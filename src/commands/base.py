from __future__ import annotations
from discord.ext.commands import Cog
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from src.client.base import ClientBase


class BaseCommands(Cog):
    def __init__(self, client: ClientBase):
        self.client = client
