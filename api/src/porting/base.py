from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic.fields import FieldInfo
from pydantic import BaseModel

from plural.missing import MISSING

if TYPE_CHECKING:
    from .standard import StandardExport


class MissingBaseModel(BaseModel):
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs) -> None:  # noqa: ANN003
        super().__pydantic_init_subclass__(**kwargs)
        for name, field in cls.model_fields.items():
            if (
                (annotation := cls.__annotations__.get(name)) is None or
                not str(annotation).startswith('Optional[')
            ):
                continue

            cls.model_fields[name] = FieldInfo(
                default=MISSING,
                required=False,
                **{
                    k: v
                    for k, v in field._attributes_set.items()
                    if k not in {'default', 'required'}
                }
            )

        cls.model_rebuild(force=True)


class BaseExport(MissingBaseModel, ABC):
    @property
    def logs(self) -> list[str]:
        if getattr(self, '_logs', None) is None:
            self._logs: list[str] = []

        return self._logs

    @abstractmethod
    def to_standard(self) -> StandardExport:
        ...
