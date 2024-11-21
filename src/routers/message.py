from src.discord import Message, Resolved, Snowflake, MessageType, MessageFlag, User, Guild, GuildFeature, Permission, Member, Channel
from src.core.auth import api_key_validator, TokenData, Security
from src.core.models import MessageResponse, MessageSend
from src.db import Message as DBMessage, ProxyMember
from fastapi import HTTPException, Query, APIRouter
from fastapi.responses import JSONResponse
from src.logic.proxy import process_proxy
from src.docs import message as docs
from datetime import datetime, UTC
from asyncio import sleep

router = APIRouter(prefix='/message', tags=['Message'])


def _snowflake_to_age(snowflake: int) -> float:
    return (
        datetime.now(UTC) - datetime.fromtimestamp(
            ((snowflake >> 22) + 1420070400000) / 1000,
            tz=UTC)
    ).total_seconds()


class FakeMessage(Message):
    def __init__(
        self,
        channel_id: int,
        content: str,
        author: User,
        referenced_message: Message | None = None,
        **kwargs
    ) -> None:
        super().__init__(
            id=Snowflake(0),
            channel_id=Snowflake(channel_id),
            content=content,
            timestamp=datetime.now(UTC),
            mention_everyone=False,
            mentions=[],
            mention_roles=[],
            attachments=[],
            embeds=[],
            pinned=False,
            type=MessageType.DEFAULT,
            flags=MessageFlag.NONE,
            resolved=Resolved(messages={}),
            author=author,
            referenced_message=referenced_message,
            **kwargs
        )

    async def delete(
        self,
        reason: str | None = None,
        token: str | None = None
    ) -> None:
        pass


@router.get(
    '/{message_id}',
    response_model=MessageResponse,
    responses=docs.get__message)
async def get__message(
    message_id: int,
    only_check_existence: bool = Query(
        default=False,
        description='if True, returns a boolean indicating whether the message was found'),
    max_wait: int = Query(
        default=10, ge=0, le=10,
        description='the maximum time to wait for the message to be found')
) -> JSONResponse:
    _find = {
        '$or':
            [
                {'original_id': message_id},
                {'proxy_id': message_id}
            ]
    }

    message = await DBMessage.find_one(_find)

    # ? /plu/ral deletes the original message and replaces it silmultaneously
    # ? due to discord ratelimiting, the original message may be deleted before the proxy is created
    for _ in range(15):
        if message is not None or _snowflake_to_age(message_id) > max_wait:
            break

        await sleep(0.5)
        message = await DBMessage.find_one(_find, ignore_cache=True)

    if only_check_existence:
        return JSONResponse(
            content=message is not None
        )

    if message is None:
        raise HTTPException(status_code=404, detail='message not found')

    return JSONResponse(
        content=message.model_dump_json(exclude={'id'})
    )


@router.post(
    '',
    response_model=MessageResponse,
    responses=docs.post__message)
async def post__message(
    message: MessageSend,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    """

    send a message through the api, you must have the MANAGE_GUILD permission if the server has auto moderation enabled, otherwise you must have the SEND_MESSAGES and VIEW_CHANNEL permissions

    """

    try:
        channel = await Channel.fetch(message.channel_id)
    except Exception:
        raise HTTPException(404, 'channel not found')

    if channel.guild_id is None:
        raise HTTPException(
            404, 'channel not found')

    member = await ProxyMember.get(message.member_id)

    if member is None or token.user_id not in (await member.get_group()).accounts:
        raise HTTPException(404, 'member not found')

    try:
        author = await Member.fetch(channel.guild_id, token.user_id)
    except Exception:
        raise HTTPException(
            # ? using channel not found for privacy
            404, 'channel not found')

    permissions = await author.fetch_permissions_for(channel.guild_id, message.channel_id)

    guild = await Guild.fetch(channel.guild_id)

    required_permissions = (
        Permission.MANAGE_GUILD
        if GuildFeature.AUTO_MODERATION in guild.features else
        Permission.SEND_MESSAGES | Permission.VIEW_CHANNEL
    )

    if not permissions & required_permissions:
        raise HTTPException(
            403, 'you do not have permission to send messages to this channel\nif the server has auto moderation enabled, you must have the manage server permission, otherwise you must have the send messages and view channel permissions')

    referenced_message = None

    if message.reference_id is not None:
        try:
            referenced_message = await Message.fetch(
                channel.id, message.reference_id)
        except Exception:
            raise HTTPException(404, 'referenced message not found')

    assert author.user is not None

    fake_message = FakeMessage(
        channel_id=message.channel_id,
        content=message.content,
        author=author.user,
        referenced_message=referenced_message
    )

    await fake_message.populate()

    _, _, _, db_message = await process_proxy(
        fake_message,
        member=member,
    )

    if db_message is None:
        raise HTTPException(500, 'failed to send message')

    return JSONResponse(
        content=db_message.model_dump_json(exclude={'id'})
    )
