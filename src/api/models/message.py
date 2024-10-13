from pydantic import BaseModel, Field
from datetime import datetime


class MessageModel(BaseModel):
    original_id: int = Field(description='the original id of the message')
    proxy_id: int = Field(description='the proxy id of the message')
    author_id: int = Field(description='the author id of the message')
    ts: datetime = Field(description='the timestamp of the message')
