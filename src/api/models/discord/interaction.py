from __future__ import annotations
from .enums import InteractionType, InteractionContextType, CommandType, InteractionCallbackType, MessageFlags, OptionType
from pydantic import BaseModel, model_validator
from fastapi.responses import JSONResponse, Response, StreamingResponse
from aiohttp import FormData, ClientSession
from .attachment import Attachment
from .guild import PartialGuild
from .message import Message
from .channel import Channel
from .option import Option
from .member import Member
from .embed import Embed
from typing import Type
from .user import User
from json import dumps
from io import BytesIO
from base64 import b64encode
from discord.utils import _bytes_to_base64_data
from src.helpers import create_multipart


class ResolvedData(BaseModel):
    users: dict[str, User] | None = None
    members: dict[str, Member] | None = None
    roles: dict[str, dict] | None = None
    channels: dict[str, Channel] | None = None
    messages: dict[str, Message] | None = None  # !
    attachments: dict[str, Attachment] | None = None  # !


class InteractionData(BaseModel):
    id: str
    name: str
    type: CommandType
    resolved: ResolvedData | None = None  # !
    options: list[Option] | None = None  # !
    guild_id: str | None = None
    target_id: str | None = None

    @model_validator(mode='before')
    def parse_attachments(cls, values):
        resolved_attachments = values.get(
            'resolved', {}).get('attachments', {})

        if not resolved_attachments:
            return values

        for option in values.get('options', []):
            if (
                option['type'] != OptionType.ATTACHMENT.value or
                option['value'] not in resolved_attachments
            ):
                continue

            option['value'] = Attachment.model_validate(
                resolved_attachments[option['value']]
            )
        return values


class InteractionResponse:
    @staticmethod
    def pong() -> Response:
        return JSONResponse(
            content={
                'type': InteractionCallbackType.PONG.value
            }
        )

    @staticmethod
    def defer(ephermal: bool = True) -> Response:
        raise NotImplementedError('do this at some point if you need it')

    @staticmethod
    async def send_message(
        content: str | None = None,
        *,
        embed: Embed | None = None,
        embeds: list[Embed] | None = None,
        tts: bool = False,
        ephemeral: bool = True,
        attachments: list[Attachment] | None = None,
    ) -> Response:
        data = {}

        if content:
            data['content'] = content

        if embed and embeds:
            raise ValueError('Cannot have both embed and embeds')

        if embed:
            embeds = [embed]

        if embeds:  # ! maybe embed support is unnecessary
            data['embeds'] = [embed.model_dump(
                mode='json') for embed in embeds]

        if tts:
            data['tts'] = tts

        if ephemeral:
            data['flags'] = MessageFlags.EPHEMERAL.value

        if not attachments:
            return JSONResponse(
                content={
                    'type': InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE.value,
                    'data': data
                }
            )

        parsed_attachments: dict[str, Attachment] = {  # type: ignore #? i don't wanna deal with this mypy stupid
            attachment.proxy_url or attachment.url: Attachment(
                id=index,
                filename=attachment.filename,
                content_type=attachment.content_type,
                description=attachment.description,
                title=attachment.title
            )
            for index, attachment in enumerate(attachments)
            if (attachment.proxy_url or attachment.url) is not None
        }

        data['attachments'] = [
            attachment.model_dump(mode='json', exclude_none=True)
            for attachment in parsed_attachments.values()
        ]

        async with ClientSession() as session:
            boundary, body = create_multipart(
                {
                    'type': InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE.value,
                    'data': data
                },
                [
                    await (await session.get(url)).read()
                    for url in parsed_attachments.keys()
                ]
            )

        return StreamingResponse(  # ? yes this is stupid
            content=BytesIO(body),
            media_type=f'multipart/form-data; boundary={boundary}'
        )


class Interaction(BaseModel):
    id: str
    application_id: str
    type: InteractionType
    data: InteractionData | None = None
    guild: PartialGuild | None = None
    guild_id: str | None = None
    channel: Channel | None = None
    channel_id: str | None = None
    member: Member | None = None
    user: User | None = None
    token: str
    version: int
    message: dict | None = None  # !
    app_permissions: str
    locale: str | None = None
    guild_locale: str | None = None
    entitlements: list[dict]
    authorizing_integration_owners: dict
    context: InteractionContextType | None = None

    @ property
    def author(self) -> User | Member | None:
        return self.member or self.user

    @ property
    def response(self) -> Type[InteractionResponse]:
        return InteractionResponse
