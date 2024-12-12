from __future__ import annotations
from src.db import ApiKey, Group, ProxyMember, Message, Latch, Reply, CFCDNProxy
from src.utils import create_strong_task
from src.errors import PluralException
from src.core.session import session
from urllib.parse import urlparse
from asyncio import gather, sleep
from typing import TYPE_CHECKING
from src.models import project
from datetime import datetime
from .base import BaseExport
from .log import LogMessage
from pydantic import Field

if TYPE_CHECKING:
    from .standard import StandardExport
    from beanie import PydanticObjectId


class PluralExport(BaseExport):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    api_key: ApiKey | None
    groups: list[Group]
    members: list[ProxyMember]
    messages: list[Message]
    latches: list[Latch]
    replies: list[Reply]

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
    def from_standard(
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
                    LogMessage.MEMBER_NAME_TOO_LONG.format(member_name=member.name))
                continue

            proxy_tags = []

            if len(member.proxy_tags) > 15:
                self.logs.append(
                    LogMessage.TOO_MANY_TAGS.format(member_name=member.name))

            for tag in member.proxy_tags[:15]:
                if len(tag.prefix) > 50 or len(tag.suffix) > 50:
                    self.logs.append(
                        LogMessage.TAG_TOO_LONG.format(
                            member_name=member.name, prefix=tag.prefix, suffix=tag.suffix))
                    continue

                if not tag.prefix and not tag.suffix:
                    self.logs.append(
                        LogMessage.TAG_NO_PREFIX_OR_SUFFIX.format(member_name=member.name))
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

        name_counts = {}

        for group in standard.groups:
            if len(group.name) > 45:
                self.logs.append(
                    LogMessage.GROUP_NAME_TOO_LONG.format(group_name=group.name))
                continue

            if group.tag and len(group.tag) > 79:
                self.logs.append(
                    LogMessage.GROUP_TAG_TOO_LONG.format(
                        group_name=group.name, tag=group.tag))
                continue

            name_count = name_counts.get(group.name, 0)

            ported_group = Group(
                name=f'{group.name}-{name_count}' if name_count else group.name,
                accounts=set(),
                avatar=None,
                tag=group.tag
            )

            name_counts[group.name] = name_count + 1

            for member in group.members:
                ported_group.members.add(id_map[member])

            if group.avatar_url is not None:
                self.avatar_map[ported_group.id] = group.avatar_url

            self.groups.append(ported_group)

        groupless_members = [
            member
            for member in standard.members
            if member.id not in [
                member_id
                for group in standard.groups
                for member_id in group.members
            ]
        ]

        if groupless_members:
            for group in self.groups:
                if group.name == 'default':
                    break
            else:
                group = Group(
                    name='default',
                    accounts=set(),
                    avatar=None,
                    tag=None
                )
                self.groups.append(group)

            for member in groupless_members:
                group.members.add(id_map[member.id])

        self.members.extend(ported_members.values())

        return self

    def to_standard(self) -> StandardExport:
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

        existing_members.update({
            group.name: {}
            for group in self.groups
            if group.name not in existing_members
        })

        member_map = {
            member.id: member
            for member in self.members+[
                member
                for d in existing_members.values()
                for member in d.values()
            ]
        }

        for local_group in self.groups:
            changes_made = False
            if local_group.name in existing_groups:
                self.logs.append(
                    LogMessage.GROUP_EXISTS.format(group_name=local_group.name))

                group = existing_groups[local_group.name]
            else:
                local_group.accounts = {account_id}
                group = local_group
                changes_made = True

            for member_id in local_group.members:
                member = member_map[member_id]

                if member.name in existing_members[group.name]:
                    self.logs.append(
                        LogMessage.MEMBER_EXISTS.format(
                            member_name=member.name, group_name=group.name))
                    continue

                group.members.add(member.id)
                changes_made = True

                tasks.append(
                    self._save_object_with_avatar(member, url)
                    if (url := self.avatar_map.get(member_id)) is not None
                    else member.save()
                )

            if changes_made:
                tasks.append(
                    self._save_object_with_avatar(group, url)
                    if (url := self.avatar_map.get(group.id)) is not None
                    else group.save()
                )

        if not tasks:
            self.logs.append(LogMessage.NOTHING_IMPORTED)
            return self.logs

        await gather(*tasks)

        return self.logs

    async def _refresh_discord_image(self, object_type: str, object_name: str, url: str) -> str | None:
        from src.discord import Message as DiscordMessage

        message = await DiscordMessage.send(
            project.import_proxy_channel_id,
            content=url)

        for _ in range(2):
            if message.embeds and (message.embeds[0].image or message.embeds[0].thumbnail):
                break

            await sleep(1)
            message = await DiscordMessage.fetch(project.import_proxy_channel_id, message.id)
        else:
            create_strong_task(message.delete())
            self.logs.append(LogMessage.AVATAR_FAILED.format(
                object_type=object_type, object_name=object_name))
            return None

        image = message.embeds[0].image or message.embeds[0].thumbnail
        assert image is not None

        create_strong_task(message.delete())

        async with session.get(image.url) as resp:
            content_length = resp.headers.get('Content-Length')

            if content_length and int(content_length) > 8_388_608:
                self.logs.append(LogMessage.AVATAR_TOO_LARGE.format(
                    object_type=object_type, object_name=object_name))
                return None

            data = bytearray()

            async for chunk in resp.content.iter_chunked(8192):
                data.extend(chunk)

                if len(data) > 8_388_608:
                    self.logs.append(LogMessage.AVATAR_TOO_LARGE.format(
                        object_type=object_type, object_name=object_name))
                    return None

        proxy = await CFCDNProxy(target_url=url, data=bytes(data)).save()

        return proxy.proxy_url

    async def _save_object_with_avatar(self, object: ProxyMember | Group, url: str | None) -> None:
        if url is None:
            return None

        parsed = urlparse(url)
        object_type = 'member' if isinstance(object, ProxyMember) else 'group'
        object_name = object.name

        match parsed.hostname:
            case 'cdn.discordapp.com' | 'media.discordapp.net':
                url = await self._refresh_discord_image(object_type, object_name, url)
            case 'cdn.plural.gg' | 'cdn.pluralkit.me' | 'cdn.tupperbox.app':
                pass
            case _:  # ? might restrict avatar sources later
                pass

        if url is None:
            self.logs.append(
                LogMessage.AVATAR_FAILED.format(
                    object_type=object_type, object_name=object_name))
            return None

        # ? set_avatar calls a save at the end
        try:
            await object.set_avatar(url)
        except PluralException:
            self.logs.append(LogMessage.AVATAR_TOO_LARGE.format(
                object_type=object_type, object_name=object_name))
        except Exception:  # noqa: BLE001
            self.logs.append(
                LogMessage.AVATAR_FAILED.format(
                    object_type=object_type, object_name=object_name))
        else:
            await object.save()
