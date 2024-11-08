from beanie import Document
from pydantic import Field


class ApiKey(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'api_keys'
        validate_on_save = True
        use_state_management = True
        indexes = ['token']

    id: int = Field(description='user id')  # type: ignore #? mypy stupid
    token: str = Field(description='hashed api key')
