from fastapi import HTTPException, Query, APIRouter, Security
from src.core.auth import api_key_validator, TokenData
from src.core.models.message import MessagePost, MessageGet
from src.db import Message as DBMessage, ProxyMember
from fastapi.responses import JSONResponse
from src.docs import message as docs
from datetime import datetime, UTC
from asyncio import sleep

router = APIRouter(prefix='/message', tags=['Message'])


def _snowflake_to_age(snowflake: int) -> float:
    return (datetime.fromtimestamp(
        (snowflake >> 22) + 1420070400000 / 1000
    ) - datetime.now(UTC)).total_seconds()


@router.get(
    '/{message_id}',
    response_model=MessageGet,
    responses=MessageGet.__examples__)
async def get__message(
    message_id: int,
    only_check_existence: bool = Query(default=False)
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
        if message is not None or _snowflake_to_age(message_id) > 10:
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
    response_model=MessageGet,
    responses=docs.post__message)
async def post__message(
    message: MessagePost,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    from src.discord import Channel, Member, Permission, Message
    from src.logic.proxy import get_proxy_webhook, format_reply

    try:
        channel = await Channel.fetch(message.channel_id)
    except Exception:
        raise HTTPException(404, 'channel not found')

    try:
        webhook = await get_proxy_webhook(channel)
    except Exception:
        raise HTTPException(404, 'webhook not found')

    if webhook.guild_id is None or webhook.channel_id is None:
        raise HTTPException(
            400, 'invalid webhook url found, please send a message through the bot and try again')

    member = await ProxyMember.get(message.member_id)

    if member is None or token.user_id not in (await member.get_group()).accounts:
        raise HTTPException(404, 'member not found')

    try:
        author = await Member.fetch(webhook.guild_id, token.user_id)
    except Exception:
        raise HTTPException(
            403, 'you do not have permission to send messages to this channel')

    permissions = await author.fetch_permissions_for(webhook.guild_id, message.channel_id)

    if not permissions & (
        #! need to implement automod handling to enable for everyone, MANAGE_GUILD bypasses automod, so it can always send messages
        Permission.MANAGE_GUILD
        # Permission.SEND_MESSAGES |
        # Permission.VIEW_CHANNEL
    ):
        raise HTTPException(
            403, 'you do not have permission to send messages to this channel')

    proxy_content = message.content

    embed = None
    if message.reference:
        try:
            referenced_message = await Message.fetch(
                webhook.channel_id, message.reference)
        except Exception:
            raise HTTPException(404, 'referenced message not found')

        proxy_with_reply = format_reply(
            proxy_content, referenced_message)

        if isinstance(proxy_with_reply, str):
            proxy_content = proxy_with_reply
        else:
            embed = proxy_with_reply

    group = await member.get_group()

    try:
        discord_message = await webhook.execute(
            content=proxy_content,
            thread_id=(
                channel.id
                if channel.is_thread else
                None),
            wait=True,
            username=(member.name +
                      (f' {group.tag}' if group.tag else ""))[:80],
            avatar_url=member.avatar_url or group.avatar_url,
            embeds=[embed] if embed is not None else []
        )
    except Exception:
        raise HTTPException(500, 'failed to send message')

    db_message = await DBMessage(
        original_id=None,
        proxy_id=discord_message.id,
        author_id=token.user_id,
        reason='message sent through api',
    ).save()

    return JSONResponse(
        content=db_message.model_dump_json(exclude={'id'})
    )
