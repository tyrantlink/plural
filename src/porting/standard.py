from __future__ import annotations
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING
from datetime import datetime
from .base import BaseExport


if TYPE_CHECKING:
    from .tupperbox import TupperboxExport
    from .pluralkit import PluralKitExport
    from .plural import PluralExport


class StandardExport(BaseExport):
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

    def to_plural(self) -> PluralExport:
        from .plural import PluralExport
        return PluralExport.from_standard(self, self.logs)

    def to_pluralkit(self) -> PluralKitExport:
        # from .pluralkit import PluralKitExport
        # return await PluralKitExport.from_standard(self, self.logs)
        ...  # ? would be a lot of effort, so maybe not

    def to_tupperbox(self) -> TupperboxExport:
        # from .tupperbox import TupperboxExport
        # return await TupperboxExport.from_standard(self, self.logs)
        ...  # ? would be a lot of effort, so maybe not
