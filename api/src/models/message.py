from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from plural.db.enums import SupporterTier

if TYPE_CHECKING:
    from plural.db import Message, ProxyMember, Usergroup


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


class AuthorModel(BaseModel):
    name: str
    pronouns: str
    bio: str
    birthday: str
    color: int | None
    avatar_url: str | None
    supporter: bool

    @classmethod
    def from_member(
        cls,
        usergroup: Usergroup,
        member: ProxyMember
    ) -> AuthorModel:
        private = usergroup.config.private_member_info
        return cls(
            name=member.name,
            pronouns=member.pronouns if not private else '',
            bio=member.bio if not private else '',
            birthday=member.birthday if not private else '',
            color=member.color if not private else None,
            avatar_url=member.avatar_url,
            supporter=(
                usergroup.data.supporter_tier
                == SupporterTier.SUPPORTER
            )
        )
