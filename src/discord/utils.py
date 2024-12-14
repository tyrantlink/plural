from .models import Message, User, Snowflake, MessageType, MessageFlag, Resolved, MessageReference
from datetime import datetime, UTC


class FakeMessage(Message):
    def __init__(
        self,
        channel_id: int,
        content: str,
        author: User | None = None,
        referenced_message: Message | None = None,
        author_id: int | None = None,
        **kwargs  # noqa: ANN003
    ) -> None:
        if author is None and author_id is not None:
            author = User(id=Snowflake(author_id),
                          username='FakeUser', discriminator='0000')

        super().__init__(
            id=Snowflake(0),
            channel_id=Snowflake(channel_id),
            content=content,
            timestamp=datetime.now(UTC),
            mention_everyone=False,
            mentions=[],
            mention_roles=[],
            attachments=[],
            embeds=[],
            pinned=False,
            type=MessageType.DEFAULT,
            flags=MessageFlag.NONE,
            resolved=Resolved(messages={}),
            author=author,
            referenced_message=referenced_message,
            message_reference=MessageReference(
                message_id=referenced_message.id,
                channel_id=referenced_message.channel_id,
            ) if referenced_message is not None else None,
            ** kwargs
        )

    async def delete(
        self,
        reason: str | None = None,
        token: str | None = None
    ) -> None:
        pass
