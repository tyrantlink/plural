from pydantic import BaseModel, Field, model_validator
from beanie import PydanticObjectId
from datetime import datetime


class MessageModel(BaseModel):
    original_id: int | None = Field(
        description='the original id of the message; None if message sent through api')
    proxy_id: int = Field(description='the proxy id of the message')
    author_id: int = Field(description='the author id of the message')
    ts: datetime = Field(description='the timestamp of the message')


class SendMessageModel(BaseModel):
    member: PydanticObjectId = Field(
        description='the member id of the message')
    content: str = Field(
        description='the content of the message', min_length=1, max_length=2000)
    channel: int = Field(description='the channel id of the message')

    @model_validator(mode='before')
    def validate_content(cls, value):
        if value.get('content') is None:
            return value  # ? leave to standard validation

        value['content'] = value['content'].strip()

        return value
