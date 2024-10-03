from beanie import Document, PydanticObjectId
from pydantic import Field


class Latch(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'latches'
        validate_on_save = True
        use_state_management = True

    id: str = Field(description='discord guild::user id')
    enabled: bool = Field(False, description='whether the latch is enabled')
    member: PydanticObjectId | None = Field(
        description='the latched member id')
