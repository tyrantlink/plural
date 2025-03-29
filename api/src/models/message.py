from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from plural.db import Message


class MessageModel(BaseModel):
    original_id: str | None
    proxy_id: str
    author_id: str
    channel_id: str
    reason: str
    webhook_id: str | None

    @classmethod
    def from_message(cls, message: Message) -> MessageModel:
        return cls(
            original_id=(
                str(message.original_id)
                if message.original_id is not None else
                None),
            proxy_id=str(message.proxy_id),
            author_id=str(message.author_id),
            channel_id=str(message.channel_id),
            reason=message.reason,
            webhook_id=(
                str(message.webhook_id)
                if message.webhook_id is not None else
                None
            )
        )
