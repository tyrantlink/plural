from pydantic import BaseModel
from .log import LogMessage
from typing import Self


class BaseExport(BaseModel):
    @property
    def logs(self) -> list[LogMessage | str]:
        if getattr(self, '_logs', None) is None:
            self._logs: list[LogMessage | str] = []

        return self._logs

    @classmethod
    async def from_url(cls, url: str) -> Self:
        ...

    @classmethod
    async def from_dict(cls, data: dict) -> Self:
        return cls(**data)
