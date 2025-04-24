from __future__ import annotations

from typing import TYPE_CHECKING

from beanie import PydanticObjectId  # noqa: TC002
from pydantic import BaseModel

from plural.db.enums import SupporterTier

if TYPE_CHECKING:
    from plural.db import Message, ProxyMember, Usergroup


class MessageModel(BaseModel):
    original_id: str | None
    proxy_id: str
    author_id: str
    channel_id: str
    member_id: PydanticObjectId
    reason: str
    webhook_id: str | None
    reference_id: str | None
    member: AuthorModel | None

    @classmethod
    def from_message(
        cls,
        message: Message,
        member_data: tuple[Usergroup, ProxyMember] | None = None
    ) -> MessageModel:
        return cls(
            original_id=(
                str(message.original_id)
                if message.original_id is not None else
                None),
            proxy_id=str(message.proxy_id),
            author_id=str(message.author_id),
            channel_id=str(message.channel_id),
            member_id=message.member_id,
            reason=message.reason,
            webhook_id=(
                str(message.webhook_id)
                if message.webhook_id is not None else
                None),
            reference_id=(
                str(message.reference_id)
                if message.reference_id is not None else
                None),
            member=(
                AuthorModel.from_member(*member_data)
                if member_data else
                None
            )
        )


class AuthorModel(BaseModel):
    id: PydanticObjectId
    name: str
    pronouns: str
    bio: str
    birthday: str
    color: int | None
    avatar_url: str | None
    supporter: bool
    private: bool

    @classmethod
    def from_member(
        cls,
        usergroup: Usergroup,
        member: ProxyMember
    ) -> AuthorModel:
        private = usergroup.config.private_member_info
        return cls(
            id=member.id,
            name=member.name,
            pronouns=member.pronouns if not private else '',
            bio=member.bio if not private else '',
            birthday=member.birthday if not private else '',
            color=member.color if not private else None,
            avatar_url=member.avatar_url,
            supporter=(
                usergroup.data.supporter_tier
                == SupporterTier.SUPPORTER),
            private=private
        )
