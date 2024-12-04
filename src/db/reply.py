from src.discord.http import File, get_from_cdn
from beanie import Document, PydanticObjectId
from datetime import datetime, timedelta
from pydantic import Field, BaseModel
from pymongo import IndexModel
from io import BytesIO


class Reply(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'replies'
        validate_on_save = True
        use_state_management = True
        indexes = [
            ('bot_id', 'channel'),  # ? compound index
            IndexModel('ts', expireAfterSeconds=300)
        ]

    class Attachment(BaseModel):
        url: str = Field(description='the url of the attachment')
        filename: str = Field(description='the filename of the attachment')
        description: str | None = Field(
            None, description='the description of the attachment')

        async def as_file(self) -> File:
            return File(
                BytesIO(await get_from_cdn(self.url)),
                filename=self.filename,
                description=self.description,
                spoiler=self.filename.startswith('SPOILER_')
            )

    id: PydanticObjectId = Field(  # type: ignore
        default_factory=PydanticObjectId)
    bot_id: int = Field(description='bot id')
    channel: int = Field(description='the channel id of the reply')
    content: str | None = Field(description='the userproxy content')
    attachment: Attachment | None = Field(
        description='the message attachment')
    ts: datetime = Field(
        default_factory=datetime.utcnow,
        description='timestamp for the reply; used for ttl')
