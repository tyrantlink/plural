from __future__ import annotations
from .avatar_decoration import AvatarDecorationData  # noqa: TC001
from .enums import GuildMemberFlag, Permission
from src.discord.http import Route, request
from src.db import DiscordCache, CacheType
from src.discord.types import Snowflake  # noqa: TC001
from datetime import datetime, timezone
from src.errors import HTTPException
from .base import RawBaseModel
from .channel import Channel
from .guild import Guild
from .user import User  # noqa: TC001


class Member(RawBaseModel):
    user: User | None = None
    nick: str | None = None
    avatar: str | None = None
    banner: str | None = None
    roles: list[Snowflake] | None = None
    joined_at: datetime | None = None
    premium_since: datetime | None = None
    deaf: bool | None = None
    mute: bool | None = None
    flags: GuildMemberFlag
    pending: bool | None = None
    permissions: Permission | None = None
    communication_disabled_until: datetime | None = None
    avatar_decoration_data: AvatarDecorationData | None = None

    @property
    def communication_disabled(self) -> bool:
        return (
            self.communication_disabled_until is not None
            and self.communication_disabled_until > datetime.now(timezone.utc)
        )

    @classmethod
    async def fetch(cls, guild_id: Snowflake | int, user_id: Snowflake | int) -> Member:
        cached = await DiscordCache.get_member(user_id, guild_id)

        if cached is not None and not cached.deleted and cached.error is None:
            return cls(**cached.data)

        if cached is not None and cached.exception:
            raise cached.exception

        try:
            data = await request(Route(
                'GET',
                '/guilds/{guild_id}/members/{user_id}',
                guild_id=guild_id,
                user_id=user_id))
        except HTTPException as e:
            if 400 <= e.status_code < 500:
                await DiscordCache.http4xx(
                    e.status_code,
                    CacheType.MEMBER,
                    user_id,
                    guild_id)
            raise

        member = cls(**data)

        await DiscordCache.add(
            type=CacheType.MEMBER,
            data=data,
            guild_id=guild_id
        )

        return member

    async def fetch_permissions_for(
        self,
        guild_id: Snowflake | int,
        channel_id: Snowflake | int,
    ) -> Permission:
        if self.user is None:
            raise ValueError('User not found')

        # ? compute base permissions
        guild = await Guild.fetch(guild_id)

        if guild.owner_id == self.user.id:
            return Permission.all()

        if not guild.roles:
            raise ValueError('Roles not found')

        # ? everyone role
        permissions = next(
            role.permissions
            for role in guild.roles
            if role.id == guild.id
        )

        for role in [
            role
            for role in guild.roles
            if role.id in
            (self.roles or [])
        ]:
            permissions |= role.permissions

        if permissions & Permission.ADMINISTRATOR:
            return Permission.all()

        # ? compute channel overwrites
        channel = await Channel.fetch(channel_id)

        if channel.is_thread and channel.parent_id is not None:
            channel = await Channel.fetch(channel.parent_id)

        overwrites: dict[Snowflake | int, tuple[Permission, Permission]] = {
            overwrite.id: (overwrite.allow, overwrite.deny)
            for overwrite in channel.permission_overwrites or []
        }

        # ? @everyone overwrite
        if (overwrite := overwrites.pop(guild_id, None)) is not None:
            permissions &= ~overwrite[1]  # ? deny
            permissions |= overwrite[0]  # ? allow

        # ? role overwrites
        role_allow = Permission.NONE
        role_deny = Permission.NONE
        for role_id in self.roles or []:
            if (overwrite := overwrites.pop(role_id, None)) is not None:
                role_deny |= overwrite[1]  # ? deny
                role_allow |= overwrite[0]  # ? allow

        permissions &= ~role_deny
        permissions |= role_allow

        # ? member overwrite
        if (overwrite := overwrites.pop(self.user.id, None)) is not None:
            permissions &= ~overwrite[1]
            permissions |= overwrite[0]

        if self.communication_disabled:
            permissions &= (
                Permission.VIEW_CHANNEL |
                Permission.READ_MESSAGE_HISTORY
            )

        return permissions
