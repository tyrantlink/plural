from .listeners import ClientListeners
from src.commands import Commands
from .base import ClientBase


class Client(ClientListeners, ClientBase):
    async def start(self, token: str, *, reconnect: bool = True) -> None:
        self.add_cog(Commands(self))
        await self.db.connect()
        await self.login(token)
        await self.connect(reconnect=reconnect)
