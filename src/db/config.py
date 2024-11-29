from datetime import timedelta
from beanie import Document
from pydantic import Field


class Config(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'config'
        use_cache = True
        validate_on_save = True
        use_state_management = True
        cache_expiration_time = timedelta(seconds=30)

    id: int = Field(  # type: ignore
        description='either guild id or user id; currently always guild id')
    logclean: bool = Field(
        default=False,
        description='whether the log cleaning is enabled')
