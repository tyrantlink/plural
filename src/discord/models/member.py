from __future__ import annotations
from .avatar_decoration import AvatarDecorationData
from .enums import GuildMemberFlag, Permission
from src.discord.http import Route, request
from src.discord.types import Snowflake
from datetime import datetime, timezone
from .base import RawBaseModel
from .channel import Channel
from .guild import Guild
from .user import User


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
    async def fetch(cls, guild_id: Snowflake, user_id: Snowflake) -> Member:
        return cls(
            **await request(
                Route(
                    'GET',
                    '/guilds/{guild_id}/members/{user_id}',
                    guild_id=guild_id,
                    user_id=user_id
                )
            )
        )

    async def fetch_permissions_for(
        self,
        guild_id: Snowflake,
        channel_id: Snowflake,
    ) -> Permission:
        if self.user is None:
            raise ValueError('User not found')

        # ? compute base permissions
        guild = await Guild.fetch(guild_id)

        if guild.owner_id == self.user.id:
            return Permission.all()

        permissions = Permission.NONE

        for role in [
            role
            for role in guild.roles or []
            if role.id in
            (self.roles or [])
        ]:
            permissions |= role.permissions

        if permissions & Permission.ADMINISTRATOR:
            return Permission.all()

        # ? compute channel overwrites
        channel = await Channel.fetch(channel_id)

        overwrites: dict[Snowflake, tuple[Permission, Permission]] = {
            overwrite.id: (overwrite.allow, overwrite.deny)
            for overwrite in channel.permission_overwrites or []
        }

        # ? @everyone overwrite
        if (overwrite := overwrites.pop(guild_id, None)) is not None:
            permissions &= ~overwrite[0]
            permissions |= overwrite[1]

        # ? role overwrites
        for role_id in self.roles or []:
            if (overwrite := overwrites.pop(role_id, None)) is not None:
                permissions &= ~overwrite[0]
                permissions |= overwrite[1]

        # ? member overwrite
        if (overwrite := overwrites.pop(self.user.id, None)) is not None:
            permissions &= ~overwrite[0]
            permissions |= overwrite[1]

        if self.communication_disabled:
            permissions &= (
                Permission.VIEW_CHANNEL |
                Permission.READ_MESSAGE_HISTORY
            )

        return permissions
