from __future__ import annotations
from discord import ApplicationContext, Attachment, TextChannel
from aiohttp import ClientSession, ClientTimeout
from typing import Self, TYPE_CHECKING
from beanie import PydanticObjectId
from src.db.models import ProxyTag
from src.helpers import send_error
from .embed import ImportHelpEmbed
from urllib.parse import urlparse
from asyncio import sleep, gather
from src.db import Member, Group
from src.project import project
from asyncio import create_task
from .models import ImportType
from typing import Any
from json import loads

if TYPE_CHECKING:
    from src.client import Client


class ImportHandler:
    def __init__(self, data: dict, client: Client) -> None:
        self.data = data
        self.client = client
        self.type = ImportType.TUPPERBOX if 'tuppers' in data else ImportType.PLURALKIT
        self.log: list[str] = []

    @classmethod
    async def from_attachment(
        cls,
        ctx: ApplicationContext,
        attachment: Attachment,
        client: Client
    ) -> Self | None:
        if attachment.content_type is not None and 'application/json' not in attachment.content_type:
            await send_error(ctx, 'file must be a json file')
            return None

        if attachment.size > 2 ** 22:  # 4MB
            await send_error(ctx, 'file is too large, 4MB max')
            return None

        try:
            json_data = loads(await attachment.read())
        except Exception as e:
            await send_error(ctx, f'error reading file: {e}')
            return None

        return cls(json_data, client)

    @classmethod
    async def from_url(
        cls,
        ctx: ApplicationContext,
        url: str,
        client: Client
    ) -> Self | None:
        url_data = urlparse(url)

        if url_data.scheme != 'https':
            await send_error(ctx, 'url must be https')
            return None

        if url_data.hostname != 'cdn.discordapp.com':
            await send_error(ctx, 'url must be a discord cdn url')
            return None

        async with ClientSession(timeout=ClientTimeout(10)) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await send_error(ctx, 'error fetching file, try to upload it instead')
                    return None

                content = bytearray()

                async for chunk in response.content.iter_chunked(1024):
                    content.extend(chunk)
                    if len(content) > 2 ** 22:  # 4MB
                        await send_error(ctx, 'file is too large to import, 4MB max')
                        return None

                try:
                    json_data = loads(content)
                except Exception as e:
                    await send_error(ctx, f'error reading file: {e}')
                    return None

                return cls(json_data, client)

    async def _refresh_discord_attachment(self, url: str) -> str | None:
        channel = self.client.get_channel(project.import_proxy_channel_id)

        if not isinstance(channel, TextChannel):
            return None  # ? should never happen

        message = await channel.send(url)

        for _ in range(5):
            if message.embeds:
                create_task(message.delete())
                return (
                    message.embeds[0].image.url
                    if message.embeds[0].image
                    else message.embeds[0].thumbnail.url
                    if message.embeds[0].thumbnail
                    else None
                )
            await sleep(1)
            try:
                message = await channel.fetch_message(message.id)
            except Exception as e:
                return None

        return None

    async def _url_to_image(self, url: str | None, name: str) -> PydanticObjectId | None:
        if url is None:
            return None

        url_data = urlparse(url)

        if url_data.scheme != 'https':
            self.log.append(
                f'failed to port `{name}` avatar, url must be https')
            return None

        file_extension = url_data.path.rsplit('.', 1)[-1]

        if file_extension not in {'png', 'jpg', 'jpeg', 'gif', 'webp'}:
            self.log.append(
                f'failed to port `{name}` avatar, image must be a png, jpg, jpeg, gif, or webp')
            return None

        async with ClientSession(timeout=ClientTimeout(10)) as session:
            async with session.get(url) as response:
                if url_data.hostname == 'cdn.discordapp.com' and response.status == 404:
                    return await self._url_to_image(
                        await self._refresh_discord_attachment(url),
                        name,

                    )

                if response.status != 200:
                    self.log.append(
                        f'failed to fetch image from url {url}, status code {response.status}')
                    return None

                if response.content_type not in {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}:
                    self.log.append(
                        f'failed to port `{name}` avatar, image must be a png, jpg, jpeg, gif, or webp')
                    return None

                content = bytearray()

                async for chunk in response.content.iter_chunked(1024):
                    content.extend(chunk)
                    if len(content) > 2 ** 22:
                        self.log.append(
                            f'failed to port `{name}` avatar, image is too large, 4MB max')
                        return None

        image = self.client.db.new.image(
            data=content,
            extension=file_extension
        )

        await image.save()

        return image.id

    async def _save_object_with_avatar(self, obj: Member | Group, avatar_url: str) -> None:
        obj.avatar = await self._url_to_image(avatar_url, obj.name)
        await obj.save()

    async def _from_pluralkit(self, user_id: int) -> bool:
        tasks = []
        pk_groups = {
            group['name']: group['members']
            for group in self.data['groups']
        }

        def get_member_group(member_id: str) -> str:
            for group in pk_groups:
                if member_id in pk_groups[group]:
                    return group
            return 'default'

        new_groups: dict[str, list[dict[str, Any]]] = {}

        for member in self.data['members']:
            member_group = get_member_group(member['id'])

            if member_group not in new_groups:
                new_groups[member_group] = []

            new_groups[member_group].append({
                'name': member['name'],
                'avatar_url': member['avatar_url'],
                'proxy_tags': member['proxy_tags']
            })

        existing_groups = {
            group.name: group
            for group in await self.client.db.groups(user_id)
        }

        for group_name, members in new_groups.items():
            if group_name in existing_groups:
                group = existing_groups[group_name]
            else:
                group = self.client.db.new.group(group_name)
                group.tag = self.data['tag']
                group.accounts.add(user_id)
                tasks.append(self._save_object_with_avatar(
                    group, self.data['avatar_url']))

            existing_group_members = [
                member.name
                for member in
                await group.get_members()
            ]

            for member in members:
                if member['name'] in existing_group_members:
                    self.log.append(
                        f'failed to port member {member['name']} to group {group_name}, member already exists')
                    continue

                member_model = await group.add_member(
                    member['name'],
                    save=False
                )

                for tag in member['proxy_tags']:
                    member_model.proxy_tags.append(
                        ProxyTag(
                            prefix=tag['prefix'] or '',
                            suffix=tag['suffix'] or '',
                            regex=False
                        ))

                tasks.append(self._save_object_with_avatar(
                    member_model, member['avatar_url']))

        await gather(*tasks)

        return True

    async def _from_tupperbox(self, user_id: int) -> bool:
        tasks = []
        tb_groups = {
            group['id']: group['name']
            for group in self.data['groups']
        }

        if any((group.get('avatar') != None for group in self.data['groups'])):
            self.log.append(
                'warning: some of your groups have avatars, porting tupperbox group avatars is not supported')

        existing_groups = {
            group.name: group
            for group in await self.client.db.groups(user_id)
        }

        if 'default' not in existing_groups:
            group = self.client.db.new.group('default')
            group.accounts.add(user_id)
            await group.save()
            existing_groups['default'] = group

        for member in self.data['tuppers']:
            member_group = tb_groups.get(member['group_id'], 'default')

            if member['group_id'] is not None and member_group not in existing_groups:
                group = self.client.db.new.group(member_group)
                group.tag = [
                    group['tag']
                    for group in self.data['groups']
                    if group['id'] == member['group_id']
                ][0]
                group.accounts.add(user_id)
                await group.save()
                existing_groups[member_group] = group
            else:
                group = existing_groups[member_group]

            if member['name'] in [
                member.name
                for member in await group.get_members()
            ]:
                self.log.append(
                    f'failed to port member {member['name']} to group {group.name}, member already exists')
                continue

            member_model = await group.add_member(
                member['name'],
                save=False
            )

            if member['brackets']:
                member_model.proxy_tags.append(
                    ProxyTag(
                        prefix=member['brackets'][0],
                        suffix=member['brackets'][1],
                        regex=False
                    ))

            tasks.append(self._save_object_with_avatar(
                member_model, member['avatar_url'] or None))

            tasks.append(group.save())

        await gather(*tasks)

        return True

    async def import_to_plural(self, ctx: ApplicationContext) -> bool:
        match self.type:
            case ImportType.PLURALKIT:
                return await self._from_pluralkit(ctx.author.id)
            case ImportType.TUPPERBOX:
                return await self._from_tupperbox(ctx.author.id)

        return False
