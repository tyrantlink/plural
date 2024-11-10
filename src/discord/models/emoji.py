from __future__ import annotations
from src.discord.http import get_from_cdn, request, Route, _bytes_to_base64_data
from src.discord.types import Snowflake
from .base import RawBaseModel
from .user import User

__all__ = ('Emoji',)


class Emoji(RawBaseModel):
    id: Snowflake | None
    name: str | None
    roles: list[Snowflake] | None = None
    user: User | None = None
    require_colons: bool | None = None
    managed: bool | None = None
    animated: bool | None = None
    available: bool | None = None

    def __str__(self) -> str:
        return f'<{"a" if self.animated else ""}:{self.name}:{self.id}>'

    async def read(self) -> bytes:
        return await get_from_cdn(
            f'https://cdn.discordapp.com/emojis/{self.id}.{"gif" if self.animated else "png"}')

    @classmethod
    async def create_application_emoji(
        cls,
        name: str,
        image: bytes
    ) -> Emoji:
        return cls(
            **await request(
                Route(
                    'POST',
                    '/applications/{application_id}/emojis'
                ),
                json={
                    'name': name,
                    'image': _bytes_to_base64_data(image)
                }
            )
        )

    async def delete(self) -> None:
        await request(
            Route(
                'DELETE',
                '/applications/{application_id}/emojis/{emoji_id}',
                emoji_id=self.id
            )
        )
