from __future__ import annotations
from .attachment import Attachment
from pydantic import BaseModel
from .enums import OptionType


class Option(BaseModel):
    name: str
    type: OptionType
    value: str | int | float | bool | Attachment | None = None
    options: list[Option] | None = None
    focused: bool | None = None
