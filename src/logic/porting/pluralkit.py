from __future__ import annotations
from pydantic import BaseModel, Field
from typing import TYPE_CHECKING
from datetime import datetime
from .base import BaseExport

if TYPE_CHECKING:
    from .standard import StandardExport


class PluralKitExport(BaseExport):
    async def to_standard(self) -> StandardExport:
        ...
