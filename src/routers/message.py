from src.discord import Message, Guild, GuildFeature, Permission, Member, Channel
from src.core.auth import api_key_validator, TokenData, Security
from src.core.models import MessageResponse, MessageSend
from fastapi.responses import JSONResponse, Response
from src.db import Message as DBMessage, ProxyMember
from fastapi import HTTPException, Query, APIRouter
from src.discord.utils import FakeMessage
from src.logic.proxy import process_proxy
from src.docs import message as docs
from src.models import DebugMessage
from datetime import datetime, UTC
from asyncio import sleep

router = APIRouter(prefix='/message', tags=['Message'])


def _snowflake_to_age(snowflake: int) -> float:
    return (
        datetime.now(UTC) - datetime.fromtimestamp(
            ((snowflake >> 22) + 1420070400000) / 1000,
            tz=UTC)
    ).total_seconds()


@router.get(
    '/{message_id}',
    response_model=MessageResponse,
    responses=docs.get__message)
async def get__message(
    message_id: int,
    only_check_existence: bool = Query(
        default=False,
        description='returns no body, only a 204 status code if the message exists'),
    max_wait: float = Query(
        default=10, ge=0, le=10,
        description='the maximum time to wait for the message to be found')
) -> Response:
    _find = {'$or': [
        {'original_id': message_id},
        {'proxy_id': message_id}
    ]}

    message = await DBMessage.find_one(_find)

    # ? /plu/ral deletes the original message and replaces it simultaneously
    # ? due to discord ratelimiting, the original message may be deleted before the proxy is created
    for _ in range(15):
        age = _snowflake_to_age(message_id)

        if message is not None or -5 < age < max_wait:
            break

        await sleep(0.5)
        message = await DBMessage.find_one(_find)

    if only_check_existence:
        return Response(status_code=204 if message is not None else 404)

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
    token: TokenData = Security(api_key_validator)  # noqa: B008
) -> JSONResponse:
    """

    send a message through the api, you must have the MANAGE_GUILD permission if the server has auto moderation enabled, otherwise you must have the SEND_MESSAGES and VIEW_CHANNEL permissions

    """

    try:
        channel = await Channel.fetch(message.channel_id)
    except Exception:  # noqa: BLE001
        raise HTTPException(404, 'channel not found') from None

    if channel.guild_id is None:
        raise HTTPException(
            404, 'channel not found')

    member = await ProxyMember.get(message.member_id)

    if member is None or token.user_id not in (await member.get_group()).accounts:
        raise HTTPException(404, 'member not found')

    try:
        author = await Member.fetch(channel.guild_id, token.user_id)
    except Exception:  # noqa: BLE001
        # ? using channel not found for privacy
        raise HTTPException(404, 'channel not found') from None

    permissions = await author.fetch_permissions_for(channel.guild_id, message.channel_id)

    guild = await Guild.fetch(channel.guild_id)

    required_permissions = (
        Permission.MANAGE_GUILD
        if guild.features and GuildFeature.AUTO_MODERATION not in guild.features else
        Permission.SEND_MESSAGES | Permission.VIEW_CHANNEL
    )

    if not permissions & required_permissions:
        raise HTTPException(
            403, 'you do not have permission to send messages to this channel\nif the server has auto moderation enabled, you must have the manage server permission, otherwise you must have the send messages and view channel permissions')

    referenced_message = None

    if message.reference_id is not None:
        try:
            referenced_message = await Message.fetch(
                channel.id,
                message.reference_id,
                include_content=True)
        except Exception:  # noqa: BLE001
            raise HTTPException(404, 'referenced message not found') from None

    assert author.user is not None

    fake_message = FakeMessage(
        channel_id=message.channel_id,
        content=message.content,
        author=author.user,
        referenced_message=referenced_message
    )

    await fake_message.populate()

    response = await process_proxy(
        fake_message,
        member=member,
    )

    if response.db_message is None:
        debug_log: list[DebugMessage | str] = [DebugMessage.ENABLER]

        await process_proxy(fake_message, debug_log, member=member)

        debug_log.remove(DebugMessage.ENABLER)

        raise HTTPException(500, {
            'reason': 'failed to send message',
            'debug': [str(log) for log in debug_log]
        })

    return JSONResponse(
        content=response.db_message.model_dump_json(exclude={'id'})
    )
