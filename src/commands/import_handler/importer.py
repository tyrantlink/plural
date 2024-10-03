from discord import ApplicationContext, Attachment
from aiohttp import ClientSession, ClientTimeout
from beanie import PydanticObjectId
from src.helpers import send_error
from src.db.models import ProxyTag
from urllib.parse import urlparse
from src.db import MongoDatabase
from .models import ImportType
from typing import Self
from json import loads


class Importer:
    def __init__(self, data: dict) -> None:
        self.data = data
        self.type = ImportType.TUPPERBOX if 'tuppers' in data else ImportType.PLURALKIT
        self.log: list[str] = []

    @classmethod
    async def from_attachment(cls, ctx: ApplicationContext, attachment: Attachment) -> Self | None:
        if attachment.content_type is not None and 'application/json' not in attachment.content_type:
            await send_error(ctx, 'file must be a json file')
            return

        if attachment.size > 2 ** 22:  # 4MB
            await send_error(ctx, 'file is too large, 4MB max')
            return

        try:
            json_data = loads(await attachment.read())
        except Exception as e:
            await send_error(ctx, f'error reading file: {e}')
            return

        return cls(json_data)

    @classmethod
    async def from_url(cls, ctx: ApplicationContext, url: str) -> Self | None:
        url_data = urlparse(url)

        if url_data.scheme != 'https':
            await send_error(ctx, 'url must be https')
            return

        if url_data.hostname != 'cdn.discordapp.com':
            await send_error(ctx, 'url must be a discord cdn url')
            return

        async with ClientSession(timeout=ClientTimeout(10)) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await send_error(ctx, 'error fetching file, try to upload it instead')
                    return

                content = bytearray()

                async for chunk in response.content.iter_chunked(1024):
                    content.extend(chunk)
                    if len(content) > 2 ** 22:  # 4MB
                        await send_error(ctx, 'file is too large to import, 4MB max')
                        return

                try:
                    json_data = loads(content)
                except Exception as e:
                    await send_error(ctx, f'error reading file: {e}')
                    return

                return cls(json_data)

    async def _url_to_image(self, url: str | None, name: str, db: MongoDatabase) -> PydanticObjectId | None:
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

        image = db.new.image(
            data=content,
            extension=file_extension
        )

        await image.save()

        return image.id

    async def _from_pluralkit(self, user_id: int, db: MongoDatabase) -> bool:
        pk_groups = {
            group['name']: group['members']
            for group in self.data['groups']
        }

        def get_member_group(member_id: str) -> str:
            for group in pk_groups:
                if member_id in pk_groups[group]:
                    return group
            return 'default'

        new_groups = {}

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
            for group in await db.groups(user_id)
        }

        for group_name, members in new_groups.items():
            if group_name in existing_groups:
                group = existing_groups[group_name]
            else:
                group = db.new.group(group_name)
                group.tag = self.data['tag']
                group.avatar = await self._url_to_image(
                    self.data['avatar_url'],
                    group_name,
                    db
                )
                group.accounts.add(user_id)
                await group.save()

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
                    member['name']
                )

                member_model.avatar = await self._url_to_image(
                    member['avatar_url'],
                    member['name'],
                    db
                )

                for tag in member['proxy_tags']:
                    member_model.proxy_tags.append(
                        ProxyTag(
                            prefix=tag['prefix'] or '',
                            suffix=tag['suffix'] or '',
                            regex=False
                        ))

                await member_model.save()

        return True

    async def _from_tupperbox(self, user_id: int, db: MongoDatabase) -> bool:
        return False

    async def import_to_plural(self, ctx: ApplicationContext, db: MongoDatabase) -> bool:
        match self.type:
            case ImportType.PLURALKIT:
                return await self._from_pluralkit(ctx.author.id, db)
            case ImportType.TUPPERBOX:
                return await self._from_tupperbox(ctx.author.id, db)

        return False
