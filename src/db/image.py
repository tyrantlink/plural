from beanie import Document, PydanticObjectId
from datetime import timedelta
from pydantic import Field


class Image(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'images'
        use_cache = True
        validate_on_save = True
        cache_expiration_time = timedelta(minutes=30)

    id: PydanticObjectId = Field(  # type: ignore
        default_factory=PydanticObjectId)
    data: bytes = Field(description='the binary data of the image')
    extension: str = Field(description='the file extension of the image')
