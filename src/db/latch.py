from beanie import Document, PydanticObjectId
from pydantic import Field
from .member import ProxyMember


class Latch(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'latches'
        validate_on_save = True
        use_state_management = True
        indexes = [('user', 'guild')]  # ? compound index

    id: PydanticObjectId = Field(  # type: ignore
        default_factory=PydanticObjectId)
    user: int = Field(description='user id')
    guild: int | None = Field(description='guild id')
    enabled: bool = Field(False, description='whether the latch is enabled')
    member: PydanticObjectId | None = Field(
        description='the latched member id')

    async def get_member(self) -> ProxyMember:
        member = await ProxyMember.find_one({'id': self.member})
        assert member is not None
        return member
