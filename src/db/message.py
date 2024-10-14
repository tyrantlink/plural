from beanie import Document, PydanticObjectId  # , TimeSeriesConfig, Granularity
from datetime import timedelta, datetime
from pydantic import Field


class Message(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'messages'
        validate_on_save = True
        cache_expiration_time = timedelta(minutes=30)
        indexes = ['original_id', 'proxy_id', 'author_id']
        # timeseries = TimeSeriesConfig( #! https://github.com/BeanieODM/beanie/issues/1005
        #     time_field='ts',
        #     granularity=Granularity.seconds,
        #     expire_after_seconds=30
        # )

    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    original_id: int | None = Field(
        description='the original id of the message; None if message sent through api')
    proxy_id: int = Field(description='the proxy id of the message')
    author_id: int = Field(description='the author id of the message')
    ts: datetime = Field(
        default_factory=datetime.now,
        description='the timestamp of the message')
