from __future__ import annotations

from typing import Self, Literal, TYPE_CHECKING
from asyncio import gather

from plural.db import (
    ProxyMember,
    Application,
    Usergroup,
    AutoProxy,
    ProxyLog,
    Message,
    Group,
    Reply,
    Share
)

from .base import BaseExport

if TYPE_CHECKING:
    from .standard import StandardExport


class PluralExport(BaseExport):
    applications: list[Application]
    autoproxies: list[AutoProxy]
    groups: list[Group]
    messages: list[Message]
    proxy_logs: list[ProxyLog]
    members: list[ProxyMember]
    replies: list[Reply]
    shares: list[Share]
    usergroup: Usergroup

    @classmethod
    def default(cls, usergroup: Usergroup) -> Self:
        return cls(
            applications=[],
            autoproxies=[],
            groups=[],
            messages=[],
            proxy_logs=[],
            members=[],
            replies=[],
            shares=[],
            usergroup=usergroup
        )

    @classmethod
    async def from_user_id(
        cls,
        user_id: int,
        format: Literal['full', 'standard']
    ) -> Self:
        usergroup = await Usergroup.get_by_user(user_id)

        self = cls.default(usergroup)

        self.groups = await Group.find({
            'account': usergroup.id
        }).to_list()

        self.members = await ProxyMember.find({
            '_id': {'$in': [
                member_id
                for group in self.groups
                for member_id in group.members]}
        }).to_list()

        if format == 'standard':
            return self

        (
            self.applications,
            self.autoproxies,
            self.messages,
            self.proxy_logs,
            self.replies,
            self.shares
        ) = await gather(
            Application.find({
                'developer': user_id
            }).to_list(),
            AutoProxy.find({
                'user': user_id
            }).to_list(),
            Message.find({
                'author_id': user_id
            }).to_list(),
            ProxyLog.find({
                'author_id': user_id
            }).to_list(),
            Reply.find({
                'bot_id': {'$in': [
                    member.userproxy.bot_id
                    for member in self.members
                    if member.userproxy is not None]}
            }).to_list(),
            Share.find({
                'sharer': user_id
            }).to_list()
        )

        return self

    async def to_standard(self) -> StandardExport:
        from .standard import StandardExport

        groups, members = [], []

        for group_index, group in enumerate(self.groups):
            groups.append(StandardExport.Group(
                id=group_index,
                name=group.name,
                avatar_url=group.avatar_url,
                channels=[
                    str(channel_id)
                    for channel_id in group.channels],
                tag=group.tag
            ))

            for member_index, member in enumerate(await group.get_members()):
                members.append(StandardExport.Member(
                    id=member_index,
                    name=member.name,
                    pronouns=member.pronouns,
                    bio=member.bio,
                    birthday=member.birthday,
                    color=member.color,
                    avatar_url=member.avatar_url,
                    proxy_tags=[
                        StandardExport.Member.ProxyTag(
                            prefix=proxy_tag.prefix,
                            suffix=proxy_tag.suffix,
                            regex=proxy_tag.regex,
                            case_sensitive=proxy_tag.case_sensitive)
                        for proxy_tag in member.proxy_tags],
                    group_id=group_index
                ))

        return StandardExport(
            groups=groups,
            members=members
        )
