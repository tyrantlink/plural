from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from pydantic import BaseModel, Field

from .base import BaseExport

if TYPE_CHECKING:
    from .standard import StandardExport


# ? exports were changed between v2 and v3, so this is a v1 export
# ? this is a legacy export that i'll probaby remove at some point


class Standardv1Export(BaseExport):
    class Group(BaseModel):
        id: int
        name: str
        avatar_url: str | None
        channels: list[str]
        tag: str | None
        members: list[int]

    class Member(BaseModel):
        class ProxyTag(BaseModel):
            prefix: str
            suffix: str
            regex: bool
            case_sensitive: bool

        id: int
        name: str
        avatar_url: str | None
        proxy_tags: list[ProxyTag]

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    groups: list[Group] = Field(default_factory=list)
    members: list[Member] = Field(default_factory=list)

    def to_standard(self) -> StandardExport:
        from .standard import StandardExport

        member_id_map = {
            member_id: group.id
            for group in self.groups
            for member_id in group.members
        }

        return StandardExport(
            timestamp=self.timestamp,
            groups=[
                StandardExport.Group(
                    id=group.id,
                    name=group.name,
                    avatar_url=group.avatar_url,
                    channels=group.channels,
                    tag=group.tag)
                for group in self.groups],
            members=[
                StandardExport.Member(
                    id=member.id,
                    name=member.name,
                    avatar_url=member.avatar_url,
                    proxy_tags=[
                        StandardExport.Member.ProxyTag
                        .model_validate(
                            proxy_tag,
                            from_attributes=True)
                        for proxy_tag in member.proxy_tags],
                    group_id=member_id_map[member.id])
                for member in self.members
            ]
        )
