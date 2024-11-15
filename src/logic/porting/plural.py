from __future__ import annotations
from src.db import ApiKey, Group, ProxyMember, Message, Latch, Reply
from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from urllib.parse import urlparse
from typing import TYPE_CHECKING
from asyncio import create_task
from src.models import project
from datetime import datetime
from .base import BaseExport
from .log import LogMessage
from asyncio import gather

if TYPE_CHECKING:
    from .standard import StandardExport


class PluralExport(BaseExport):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    api_key: ApiKey | None
    groups: list[Group]
    members: list[ProxyMember]
    messages: list[Message]
    latches: list[Latch]
    replies: list[Reply]

    @property
    def logs(self) -> list[LogMessage | str]:
        if getattr(self, '_logs', None) is None:
            self._logs: list[LogMessage | str] = []

        return self._logs

    @property
    def avatar_map(self) -> dict[PydanticObjectId, str]:
        if getattr(self, '_avatar_map', None) is None:
            self._avatar_map: dict[PydanticObjectId, str] = {}

        return self._avatar_map

    @classmethod
    async def from_account_id(cls, account_id: int) -> PluralExport:
        groups = await Group.find({'accounts': account_id}).to_list()

        members = [
            member
            for group in groups
            for member in await group.get_members()
        ]

        userproxy_bot_ids = {
            member.userproxy.bot_id
            for member in members
            if member.userproxy is not None
        }

        return cls(
            api_key=await ApiKey.find_one({'_id': account_id}),
            groups=groups,
            members=members,
            messages=await Message.find({'author_id': account_id}).to_list(),
            latches=await Latch.find({'user': account_id}).to_list(),
            replies=await Reply.find({'bot_id': {'$in': userproxy_bot_ids}}).to_list(),
        )

    @classmethod
    async def from_standard(
        cls,
        standard: StandardExport,
        logs: list[LogMessage | str]
    ) -> PluralExport:
        self = cls(
            api_key=None, groups=[],
            members=[], messages=[],
            latches=[], replies=[]
        )

        ported_members: dict[PydanticObjectId, ProxyMember] = {}
        id_map: dict[int, PydanticObjectId] = {}

        self.logs.extend(logs)

        for member in standard.members:
            if len(member.name) > 80:
                self.logs.append(
                    LogMessage.MEMBER_NAME_TOO_LONG.format(member.name))
                continue

            proxy_tags = []

            if len(member.proxy_tags) > 15:
                self.logs.append(
                    LogMessage.TOO_MANY_TAGS.format(member.name))

            for tag in member.proxy_tags[:15]:
                if len(tag.prefix) > 50 or len(tag.suffix) > 50:
                    self.logs.append(
                        LogMessage.TAG_TOO_LONG.format(member.name, tag.prefix, tag.suffix))
                    continue

                if not tag.prefix and not tag.suffix:
                    self.logs.append(
                        LogMessage.TAG_NO_PREFIX_OR_SUFFIX.format(member.name))
                    continue

                proxy_tags.append(
                    ProxyMember.ProxyTag(
                        prefix=tag.prefix,
                        suffix=tag.suffix,
                        regex=tag.regex,
                        case_sensitive=tag.case_sensitive
                    )
                )

            ported_member = ProxyMember(
                name=member.name,
                avatar=None,
                proxy_tags=proxy_tags,
                userproxy=None
            )

            if member.avatar_url is not None:
                self.avatar_map[ported_member.id] = member.avatar_url

            ported_members[ported_member.id] = ported_member
            id_map[member.id] = ported_member.id

        for group in standard.groups:
            if len(group.name) > 45:
                self.logs.append(
                    LogMessage.GROUP_NAME_TOO_LONG.format(group.name))
                continue

            if group.tag and len(group.tag) > 79:
                self.logs.append(
                    LogMessage.GROUP_TAG_TOO_LONG.format(group.tag))
                continue

            ported_group = Group(
                name=group.name,
                accounts=set(),
                avatar=None,
                tag=group.tag
            )

            for member in group.members:
                ported_group.members.add(id_map[member])

            if group.avatar_url is not None:
                self.avatar_map[ported_group.id] = group.avatar_url

            self.groups.append(ported_group)

        self.members.extend(ported_members.values())

        return self

    async def to_standard(self) -> StandardExport:
        from .standard import StandardExport
        id_map = {}

        for index, group in enumerate(self.groups):
            id_map[group.id] = index

        for index, member in enumerate(self.members):
            id_map[member.id] = index

        return StandardExport(
            groups=[
                StandardExport.Group(
                    id=id_map[group.id],
                    name=group.name,
                    avatar_url=group.avatar_url,
                    channels=[
                        str(channel_id)
                        for channel_id in group.channels],
                    tag=group.tag,
                    members=[
                        id_map[member]
                        for member in group.members])
                for group in self.groups],
            members=[
                StandardExport.Member(
                    id=id_map[member.id],
                    name=member.name,
                    avatar_url=member.avatar_url,
                    proxy_tags=[
                        StandardExport.Member.ProxyTag(
                            prefix=tag.prefix,
                            suffix=tag.suffix,
                            regex=tag.regex,
                            case_sensitive=tag.case_sensitive)
                        for tag in member.proxy_tags])
                for member in self.members
            ]
        )

    async def import_to_account(self, account_id: int) -> list[LogMessage | str]:
        tasks = []

        existing_groups = {
            group.name: group
            for group in await Group.find({'accounts': account_id}).to_list()
        }

        existing_members = {
            group.name: {
                member.name: member
                for member in await group.get_members()
            }
            for group in existing_groups.values()
        }

        for group in self.groups:
            if group.name in existing_groups:
                self.logs.append(
                    LogMessage.GROUP_EXISTS.format(group.name))
                continue

            group.accounts = {account_id}
            if (url := self.avatar_map.get(group.id)) is not None:
                tasks.append(self._save_object_with_avatar(group, url))
            else:
                tasks.append(group.save())

        for member in self.members:
            if member.name in existing_members.get(member.group.name, {}):
                self.logs.append(
                    LogMessage.MEMBER_EXISTS.format(member.name, member.group.name))
                continue

            if (url := self.avatar_map.get(member.id)) is not None:
                tasks.append(self._save_object_with_avatar(member, url))
            else:
                tasks.append(member.save())

        await gather(*tasks)

        return self.logs

    async def _refresh_discord_image(self, object_type: str, object_name: str, url: str) -> str | None:
        from src.discord import Message as DiscordMessage

        message = await DiscordMessage.send(
            project.import_proxy_channel_id,
            content=url)

        if not message.embeds:
            self.logs.append(
                LogMessage.AVATAR_FAILED.format(object_type, object_name))
            return None

        if message.embeds[0].image is None and message.embeds[0].thumbnail is None:
            self.logs.append(
                LogMessage.AVATAR_FAILED.format(object_type, object_name))
            return None

        image = message.embeds[0].image or message.embeds[0].thumbnail
        assert image is not None

        create_task(message.delete())

        return image.url

    async def _save_object_with_avatar(self, object: ProxyMember | Group, url: str | None) -> None:
        if url is None:
            return None

        parsed = urlparse(url)
        object_type = 'member' if isinstance(object, ProxyMember) else 'group'
        object_name = object.name

        match parsed.hostname:
            case 'cdn.discordapp.com':
                url = await self._refresh_discord_image(object_type, object_name, url)
            case 'cdn.plural.gg' | 'cdn.pluralkit.me' | 'cdn.tupperbox.app':
                pass
            case _:  # ? might restrict avatar sources later
                pass

        if url is None:
            self.logs.append(
                LogMessage.AVATAR_FAILED.format(object_type, object_name))
            return None

        # ? set_avatar calls a save at the end
        try:
            await object.set_avatar(url)
        except Exception as e:
            self.logs.append(
                LogMessage.AVATAR_FAILED.format(object_type, object_name))
        else:
            await object.save()
