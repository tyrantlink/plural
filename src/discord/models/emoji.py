from .base import RawBaseModel
from .types import Snowflake
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
