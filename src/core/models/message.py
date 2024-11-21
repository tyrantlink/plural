from pydantic import BaseModel, Field, model_validator
from beanie import PydanticObjectId
from datetime import datetime

__all__ = (
    'MessageResponse',
    'MessageSend'
)


class MessageResponse(BaseModel):
    original_id: int | None = Field(
        description='the original id of the message; None if message sent through api')
    proxy_id: int = Field(description='the proxy id of the message')
    author_id: int = Field(description='the author id of the message')
    reason: str = Field(
        default='none given',
        description='the reason the message was proxied')
    ts: datetime = Field(description='the timestamp of the message')


class MessageSend(BaseModel):
    member_id: PydanticObjectId = Field(
        description='the member id of the message')
    content: str = Field(
        description='the content of the message', min_length=1, max_length=2000)
    channel_id: int = Field(description='the channel/thread id of the message')
    reference_id: int | None = Field(
        None,
        description='the id of the referenced message; None if not a reply')

    @model_validator(mode='before')
    def validate_content(cls, value):
        if value.get('content') is None:
            return value  # ? leave to standard validation

        value['content'] = value['content'].strip()

        return value
