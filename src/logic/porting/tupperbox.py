from __future__ import annotations
from typing import TYPE_CHECKING, Annotated
from annotated_types import MinLen, MaxLen
from pydantic import BaseModel
from datetime import datetime
from .base import BaseExport


if TYPE_CHECKING:
    from .standard import StandardExport


class TupperboxExport(BaseExport):
    class Tupper(BaseModel):
        id: int
        name: str
        brackets: Annotated[list[str], MinLen(2), MaxLen(2)]
        avatar_url: str | None
        avatar: str | None
        banner: str | None
        posts: int
        show_brackets: bool
        birthday: datetime | None
        tag: str | None
        nick: str | None
        created_at: datetime
        group_id: int | None
        last_used: datetime | None

    class Group(BaseModel):
        id: int
        name: str
        avatar: str | None
        description: str | None
        tag: str | None

    tuppers: list[Tupper]
    groups: list[Group]

    async def to_standard(self) -> StandardExport:
        ...
