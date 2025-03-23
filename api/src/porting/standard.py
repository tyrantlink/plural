from __future__ import annotations

from asyncio import gather, Semaphore
from dataclasses import dataclass
from typing import TYPE_CHECKING
from datetime import datetime

from opentelemetry.trace import SpanKind
from pydantic import Field

from plural.db import Group as ProxyGroup, ProxyMember, Usergroup
from plural.errors import PluralException, InteractionError
from plural.otel import span, inject
from plural.env import env

from src.core.avatar import upload_avatar
from src.core.http import GENERAL_SESSION

from .base import BaseExport, MissingBaseModel

if TYPE_CHECKING:
    from beanie import PydanticObjectId

MIN_64BIT = -(2**63)
MAX_64BIT = 2**63 - 1


@dataclass
class Avatar:
    name: str
    parent_id: PydanticObjectId
    url: str


class StandardExport(BaseExport):
    class Group(MissingBaseModel):
        id: int
        name: str
        avatar_url: str | None
        channels: list[str]
        tag: str | None

    class Member(MissingBaseModel):
        class ProxyTag(MissingBaseModel):
            prefix: str
            suffix: str
            regex: bool
            case_sensitive: bool

        id: int
        name: str
        avatar_url: str | None
        proxy_tags: list[ProxyTag]
        group_id: int

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    groups: list[Group] = Field(default_factory=list)
    members: list[Member] = Field(default_factory=list)

    def to_standard(self) -> StandardExport:
        return self

    async def _refresh_urls(self, urls: list[str]) -> dict[str, str]:
        from src.core.http import GENERAL_SESSION

        refreshed: dict[str, str] = {}

        for i in range(0, len(urls), 50):
            batch = urls[i:i + 50]

            headers = {'Authorization': f'Bot {env.bot_token}'}

            inject(headers)

            response = await GENERAL_SESSION.post(
                f'{env.discord_url}/attachments/refresh-urls',
                headers=headers,
                json={'attachment_urls': batch}
            )

            if response.status != 200:
                self.logs.append('failed to refresh discord cdn urls')
                raise PluralException(await response.text())

            refreshed.update({
                refreshed.get('original', ''): refreshed.get('refreshed', '')
                for refreshed in (await response.json()).get('refreshed_urls', [])
            })

        return refreshed

    async def _get_avatar_urls(self) -> list[str]:
        avatars: list[str] = [
            group.avatar_url
            for group in self.groups
            if group.avatar_url
        ]+[
            member.avatar_url
            for member in self.members
            if member.avatar_url
        ]

        discord_avatars = [
            avatar
            for avatar in avatars
            if avatar.startswith((
                'https://cdn.discordapp.com/',
                'https://media.discordapp.net/'
            ))
        ]

        if discord_avatars:
            with span(f'refreshing {len(discord_avatars)} discord urls', kind=SpanKind.CLIENT):
                refresh_map = await self._refresh_urls(discord_avatars)
        else:
            refresh_map = {}

        for original, refreshed in refresh_map.items():
            avatars[avatars.index(original)] = refreshed

        return avatars

    async def _check_avatar(self, avatar: Avatar) -> Avatar:
        async with GENERAL_SESSION.head(avatar.url) as response:
            if response.status != 200:
                self.logs.append(
                    f'Failed to download avatar for {avatar.name}. Reason: {await response.text()}')
                raise PluralException

            if response.content_length is None:
                self.logs.append(
                    f'Avatar for {avatar.name} has no content length (the image may be corrupt)')
                raise PluralException

            if int(response.content_length) > env.max_avatar_size:
                self.logs.append(
                    f'Avatar for {avatar.name} too large')
                raise PluralException

            if response.content_type not in {
                'image/png',
                'image/jpeg',
                'image/gif',
                'image/webp'
            }:
                self.logs.append(
                    f'Avatar for {avatar.name} is not a valid image; must be png, jpg, gif, or webp')
                raise PluralException

        return avatar

    async def do_import(
        self,
        user_id: int,
        dry_run: bool,
    ) -> list[str]:
        # ? gather existing data
        usergroup = await Usergroup.get_by_user(user_id)

        groups = await ProxyGroup.find({
            '$or': [
                {'accounts': usergroup.id},
                {'users': user_id}]
        }).to_list()

        members = await ProxyMember.find({
            '_id': {'$in': {
                member_id
                for group in groups
                for member_id in group.members}}
        }).to_list()

        group_map: dict[int, ProxyGroup] = {}
        member_map: dict[int, ProxyMember] = {}
        pending_avatars: list[Avatar] = []

        group_names: set[str] = {
            group.name
            for group in groups
        }

        # ? yes this is bad but i'm tired and need v3 out
        member_names: dict[str, set[str]] = {
            group.name: {
                member.name
                for member in members
                if member.id in group.members}
            for group in groups
        }

        def _unique_name(group: str, member: str | None) -> str:
            def _name_with_index(name: str, index: int) -> str:
                return f'{name}-{index}' if index else name

            for name_index in range(10):
                if member is None:
                    if _name_with_index(group, name_index) in group_names:
                        continue
                    break

                if _name_with_index(member, name_index) in member_names[group]:
                    continue
                break
            else:
                self.logs.append(
                    f'more than 10 groups named {group}; skipping groups after 10; members will be put in default group'
                    if member is None else
                    f'more than 10 members named {member} in group {group}; skipping members after 10')
                raise PluralException('too many duplicate names')

            if name_index:
                self.logs.append('; '.join(
                    [
                        f'group {group} already exists',
                        f'using {_name_with_index(group, name_index)} instead'
                    ]
                    if member is None else
                    [
                        f'member {member} already exists in group {group}',
                        f'using {_name_with_index(member, name_index)} instead'
                    ]
                ))

            return (
                _name_with_index(group, name_index)
                if member is None else
                _name_with_index(member, name_index)
            )

        for group in self.groups:
            if len(group.name) > 45:
                self.logs.append(
                    f'group {group.name} name too long; must be 45 characters or fewer; skipping group')
                continue

            if group.tag and len(group.tag) > 79:
                self.logs.append(
                    f'group {group.name} tag too long; must be 79 characters or fewer; skipping group')
                continue

            try:
                group_name = _unique_name(group.name, None)
            except PluralException:
                continue

            group_names.add(group_name)
            member_names[group_name] = set()

            new_group = ProxyGroup(
                name=group_name,
                accounts={usergroup.id},
                avatar=None,
                channels={
                    channel
                    for channel in group.channels
                    if (
                        channel.isnumeric() and
                        MIN_64BIT <= int(channel) <= MAX_64BIT)},
                tag=group.tag,
                members=set()
            )

            group_map[group.id] = new_group
            if group.avatar_url:
                pending_avatars.append(Avatar(
                    name=f'group {group_name}',
                    parent_id=new_group.id,
                    url=group.avatar_url
                ))

        _default_group = None

        def default_group() -> ProxyGroup:
            nonlocal _default_group

            if _default_group is None:
                try:
                    _default_group = next(
                        group
                        for group in group_map.values()
                        if group.name == 'default')
                except StopIteration:
                    _default_group = ProxyGroup(
                        name='default',
                        accounts={str(user_id)},
                        avatar=None,
                        channels=set(),
                        tag=None,
                        members=set())
                    group_map[len(group_map)+1] = _default_group

            return _default_group

        for member in self.members:
            if len(member.name) > 80:
                self.logs.append(
                    f'member {member.name} name too long; must be 80 characters or fewer; skipping member')
                continue

            if len(member.proxy_tags) > 15:
                self.logs.append(
                    f'member {member.name} has too many proxy tags; must be 15 or fewer; skipping member')
                continue

            if member.group_id not in group_map:
                self.logs.append(
                    f'member {member.name} has invalid group id; skipping member')
                continue

            try:
                member_name = _unique_name(
                    group_map[member.group_id].name, member.name)
            except PluralException:
                continue

            try:
                # ? .get with default as default_group() will create a new default group
                # ? which we want to avoid if it would be unused
                # ? using a try/except to make mypy happy about the group variable type
                group = group_map[member.group_id]
            except KeyError:
                group = default_group()

            new_member = ProxyMember(
                name=member_name,
                avatar=None,
                proxy_tags=[
                    ProxyMember.ProxyTag(
                        prefix=tag.prefix,
                        suffix=tag.suffix,
                        regex=tag.regex,
                        case_sensitive=tag.case_sensitive)
                    for tag in member.proxy_tags
                ]
            )

            member_map[new_member.id] = new_member
            group.members.add(new_member.id)

            if member.avatar_url:
                pending_avatars.append(Avatar(
                    name=f'member {member_name}',
                    parent_id=new_member.id,
                    url=member.avatar_url
                ))

        current_avatar_count = await usergroup.get_avatar_count(user_id)

        if (
            (attempted_count := current_avatar_count + len(pending_avatars))
            > usergroup.data.image_limit
        ):
            raise InteractionError('\n\n'.join([
                f'You have {current_avatar_count} avatar'
                f'{'s' if current_avatar_count - 1 else ''} ',
                f'and are trying to import {len(pending_avatars)} more',
                f'Your limit is {usergroup.data.image_limit} avatars',
                f'Please delete {attempted_count - usergroup.data.image_limit} '
                'avatars and try again',
                'Both group and member avatars count towards this limit'
            ]))

        with span(f'checking {len(pending_avatars)} avatars'):
            avatar_checks = await gather(*[
                self._check_avatar(avatar)
                for avatar in pending_avatars
            ], return_exceptions=True)

        if dry_run:
            return self.logs

        valid_avatars = [
            avatar
            for avatar in avatar_checks
            if not isinstance(avatar, BaseException)
        ]

        with span(
            f'converting and uploading {len(valid_avatars)} avatars'
        ):
            semaphore = Semaphore(100)
            avatar_hashes = await gather(*[
                upload_avatar(
                    str(avatar.parent_id),
                    avatar.url,
                    GENERAL_SESSION,
                    semaphore)
                for avatar in valid_avatars
            ], return_exceptions=True)

        for hash in avatar_hashes:
            if isinstance(hash, BaseException):
                self.logs.append(str(hash))

        avatar_map = dict(zip([
            avatar.parent_id
            for avatar in valid_avatars],
            [
            hash
            if isinstance(hash, str) else
            None
            for hash in avatar_hashes],
            strict=True
        ))

        for group in group_map.values():
            group.avatar = avatar_map.get(group.id)

        for member in member_map.values():
            member.avatar = avatar_map.get(member.id)

        await gather(
            *[
                group.save()
                for group in group_map.values()
            ], *[
                member.save()
                for member in member_map.values()
            ]
        )

        return self.logs
