from dataclasses import dataclass
from discord import HTTPClient


@dataclass(frozen=True)
class ProbableEmoji:
    name: str
    id: int
    animated: bool

    def __str__(self) -> str:
        return f'<{"a" if self.animated else ""}:{self.name}:{self.id}>'

    async def read(self, http: HTTPClient) -> bytes:
        return await http.get_from_cdn(
            f'https://cdn.discordapp.com/emojis/{self.id}.{"gif" if self.animated else "png"}')
