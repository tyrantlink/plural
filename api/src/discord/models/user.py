from __future__ import annotations

from typing import TYPE_CHECKING

from orjson import dumps

from plural.missing import is_not_missing, MISSING

from src.core.http import request, Route
from src.core.models import env

from src.discord.models.base import RawBaseModel
from src.discord.enums import MessageFlag

from .message import Message, AllowedMentions

if TYPE_CHECKING:
    from plural.missing import Optional, Nullable

    from src.discord.enums import UserFlag, PremiumType
    from src.discord.types import Snowflake
    from src.core.http import File

    from .avatar_decoration import AvatarDecorationData
    from .component import MessageComponent
    from .embed import Embed
    from .guild import Guild
    from .poll import Poll
    from .user import User


__all__ = (
    'User',
)


class User(RawBaseModel):
    id: Snowflake
    """the user's id"""
    username: str
    """the user's username, not unique across the platform"""
    discriminator: str
    """the user's Discord-tag"""
    global_name: Nullable[str]
    """the user's display name, if it is set. For bots, this is the application name"""
    avatar: Nullable[str]
    """the user's avatar hash"""
    bot: Optional[bool]
    """whether the user belongs to an OAuth2 application"""
    system: Optional[bool]
    """whether the user is an Official Discord System user (part of the urgent message system)"""
    mfa_enabled: Optional[bool]
    """whether the user has two factor enabled on their account"""
    banner: Optional[Nullable[str]]
    """the user's banner hash"""
    accent_color: Optional[Nullable[int]]
    """the user's banner color encoded as an integer representation of hexadecimal color code"""
    locale: Optional[str]
    """the user's chosen language option"""
    verified: Optional[bool]
    """whether the email on this account has been verified"""
    email: Optional[Nullable[str]]
    """the user's email"""
    flags: Optional[UserFlag]
    """the flags on a user's account"""
    premium_type: Optional[PremiumType]
    """the type of Nitro subscription on a user's account"""
    public_flags: Optional[UserFlag]
    """the public flags on a user's account"""
    avatar_decoration_data: Optional[Nullable[AvatarDecorationData]]
    """data for the user's avatar decoration"""

    @property
    def display_name(self) -> str:
        return self.global_name or self.username

    @property
    def default_avatar_url(self) -> str:
        avatar = (
            (self.id >> 22) % 6
            if self.discriminator in {None, '0000'} else
            int(self.discriminator) % 5)

        return f'https://cdn.discordapp.com/embed/avatars/{avatar}.png'

    @property
    def avatar_url(self) -> str:
        if self.avatar is None:
            return self.default_avatar_url

        return 'https://cdn.discordapp.com/avatars/{id}/{avatar}.{format}?size=1024'.format(
            id=self.id,
            avatar=self.avatar,
            format='gif' if self.avatar.startswith('a_') else 'png'
        )

    @classmethod
    async def fetch(
        cls,
        user_id: Snowflake,
        token: str
    ) -> User:
        return cls(
            **await request(Route(
                'GET',
                '/users/{user_id}',
                user_id=user_id,
                token=token
            ))
        )

    @classmethod
    async def fetch_from_oauth(
        cls,
        token: str
    ) -> User:
        return cls(
            **await request(Route(
                'GET',
                '/users/@me'
            ), headers={
                'Authorization': f'Bearer {token}'
            })
        )

    async def fetch_guilds(
        self,
        token: str
    ) -> list[Guild]:
        from .guild import Guild

        return [
            Guild(**guild)
            for guild in
            await request(Route(
                'GET',
                '/users/@me/guilds',
                token=token
            ))
        ]

    async def send_message(
        self,
        content: Optional[Nullable[str]] = None,
        *,
        tts: Optional[bool] = MISSING,
        embeds: Optional[Nullable[list[Embed]]] = MISSING,
        allowed_mentions: Optional[Nullable[AllowedMentions]] = MISSING,
        flags: Optional[Nullable[MessageFlag]] = MessageFlag.EPHEMERAL,
        components: Optional[Nullable[list[MessageComponent]]] = MISSING,
        attachments: Optional[Nullable[list[File]]] = MISSING,
        poll: Optional[Nullable[Poll]] = MISSING
    ) -> Message:
        json, form = {}, None

        if is_not_missing(content):
            json['content'] = content

        if is_not_missing(tts):
            json['tts'] = tts

        if is_not_missing(embeds):
            json['embeds'] = [
                embed.as_payload()
                for embed in embeds or []
            ]

        if is_not_missing(allowed_mentions):
            json['allowed_mentions'] = (
                allowed_mentions.as_payload()
                if allowed_mentions is not None
                else {}
            )

        if isinstance(flags, type(MISSING)):
            flags = MessageFlag.NONE

        json['flags'] = (
            flags.value
            if flags
            else flags
        )

        if is_not_missing(components):
            json['components'] = [
                component.as_payload()
                for component in components or []
            ]

        if is_not_missing(poll):
            json['poll'] = (
                poll.as_payload()
                if poll is not None
                else {}
            )

        if attachments:
            form, json_attachments = [], []

            for index, attachment in enumerate(attachments):
                json_attachments.append(attachment.as_payload(index))
                form.append(attachment.as_form_dict(index))

                if attachment.is_voice_message:
                    json['flags'] = (
                        json.get('flags', 0) | MessageFlag.IS_VOICE_MESSAGE
                    )

            json['attachments'] = json_attachments

        if form:
            form.insert(0, {
                'name': 'payload_json',
                'value': dumps(json).decode()
            })

        request_args = (
            {
                'form': form,
                'files': attachments
            }
            if attachments else
            {
                'json': json
            }
        )

        channel = await request(Route(
            'POST',
            '/users/@me/channels',
            token=env.bot_token
        ), json={'recipient_id': str(self.id)})

        message = await request(Route(
            'POST',
            '/channels/{channel_id}/messages',
            channel_id=channel['id'],
            token=env.bot_token
        ), **request_args)

        return Message(**message)
