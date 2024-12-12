from beanie import Document, PydanticObjectId
from datetime import datetime, timedelta
from src.models import project
from pymongo import IndexModel
from typing import ClassVar
from pydantic import Field


class CFCDNProxy(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'cfcdnproxy'
        use_cache = True
        validate_on_save = True
        cache_expiration_time = timedelta(seconds=120)
        indexes: ClassVar = [
            IndexModel('ts', expireAfterSeconds=300)
        ]

    id: PydanticObjectId = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        default_factory=PydanticObjectId)
    target_url: str = Field(description='the url of the image')
    data: bytes = Field(description='the image data')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp for the image; used for ttl')

    @property
    def proxy_url(self) -> str:
        return f'{project.api_url}/discord/imageproxy/{self.id}'
