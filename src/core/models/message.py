from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from .base import excluded_model
from src.db import Message


MessageGet = excluded_model(
    original_model=Message,
    exclude_fields=[
        '_id',
        'revision_id'
    ]
)


class MessagePost(BaseModel):
    channel_id: int = Field(
        description='the channel or thread to send the message to'
    )
    content: str = Field(
        description='the content of the message'
    )
    member_id: PydanticObjectId = Field(
        description='the member sending the message'
    )
    reference: int | None = Field(
        None,
        description='the id of the message to reply to'
    )
