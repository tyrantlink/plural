from __future__ import annotations

from typing import TYPE_CHECKING
from contextlib import suppress
from datetime import datetime  # noqa: TC003

from pydantic import Field

from .base import BaseExport, MissingBaseModel

if TYPE_CHECKING:
    from .standard import StandardExport


class TupperboxExport(BaseExport):
    class Tupper(MissingBaseModel):
        id: int
        name: str
        brackets: list[str] = Field(min_length=2, max_length=2)
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

    class Group(MissingBaseModel):
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
                    break
        else:
            self.logs.append(
                'Unable to extract user ID from tupperbox export; group avatars will not be imported')

        groups = {
            group.id: StandardExport.Group(
                id=index,
                name=group.name,
                avatar_url=(
                    f'https://cdn.tupperbox.app/group-pfp/{user_id}/{group.avatar}.webp'
                    if group.avatar is not None and user_id is not None
                    else None),
                channels=[],
                tag=group.tag)
            for index, group in enumerate(self.groups)
        }

        _default_group_id = None

        def default_group_id() -> int:
            nonlocal _default_group_id

            if _default_group_id is None:
                try:
                    _default_group_id = next(
                        group.id
                        for group in groups.values()
                        if group.name == 'default')
                except StopIteration:
                    _default_group_id = len(groups)+1

                    groups[_default_group_id] = StandardExport.Group(
                        id=_default_group_id,
                        name='default',
                        avatar_url=None,
                        channels=[],
                        tag=None
                    )

            return _default_group_id

        members = [
            StandardExport.Member(
                id=index,
                name=tupper.name,
                pronouns='',
                bio='',
                birthday=(
                    f'<t:{tupper.birthday.timestamp()}:D>'
                    if tupper.birthday is not None else ''),
                color=None,
                avatar_url=tupper.avatar_url,
                proxy_tags=[StandardExport.Member.ProxyTag(
                    prefix=tupper.brackets[0],
                    suffix=tupper.brackets[1],
                    regex=False,
                    case_sensitive=False)],
                group_id=groups[tupper.group_id].id if tupper.group_id is not None else default_group_id())
            for index, tupper in enumerate(self.tuppers)
        ]

        return StandardExport(
            groups=list(groups.values()),
            members=members
        )
