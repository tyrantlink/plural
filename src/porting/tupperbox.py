from __future__ import annotations
from typing import TYPE_CHECKING, Annotated
from annotated_types import MinLen, MaxLen
from contextlib import suppress
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
        created_at: datetime | None
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

    def to_standard(self) -> StandardExport:
        from .standard import StandardExport

        user_id = None

        for tupper in self.tuppers:
            if (
                tupper.avatar_url is not None and
                tupper.avatar_url.startswith('https://cdn.tupperbox.app/pfp/')
            ):
                with suppress(IndexError):
                    user_id = tupper.avatar_url.split('/')[4]

        groups = {
            group.id: StandardExport.Group(
                id=self.groups.index(group),
                name=group.name,
                avatar_url=(
                    f'https://cdn.tupperbox.app/group-pfp/{user_id}/{group.avatar}.webp'
                    if group.avatar is not None and user_id is not None
                    else None),
                channels=[],
                tag=group.tag,
                members=[])
            for group in self.groups
        }

        members = []

        for tupper in self.tuppers:
            if tupper.group_id:
                groups[tupper.group_id].members.append(
                    self.tuppers.index(tupper))

            members.append(StandardExport.Member(
                id=self.tuppers.index(tupper),
                name=tupper.name,
                avatar_url=tupper.avatar_url,
                proxy_tags=[StandardExport.Member.ProxyTag(
                    prefix=tupper.brackets[0],
                    suffix=tupper.brackets[1],
                    regex=False,
                    case_sensitive=False
                )]
            ))

        return StandardExport(
            groups=list(groups.values()),
            members=members
        )
