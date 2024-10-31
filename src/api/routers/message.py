from discord import Webhook as DiscordWebhook, InvalidArgument, Object, MISSING, AllowedMentions
from src.api.models.message import MessageModel, SendMessageModel
from src.db import Message, Webhook as DBWebhook, Member, Image
from src.api.drest import user_can_send, insert_reference_text
from fastapi import HTTPException, Query, APIRouter, Security
from src.api.auth import api_key_validator, TokenData
from fastapi.responses import JSONResponse
from src.api.docs import message as docs
from datetime import datetime, UTC
from aiohttp import ClientSession
from src.models import project
from asyncio import sleep

router = APIRouter(prefix='/message', tags=['Message'])


def _snowflake_to_age(snowflake: int) -> float:
    return (datetime.fromtimestamp(
        (snowflake >> 22) + 1420070400000 / 1000
    ) - datetime.now(UTC)).total_seconds()


@router.get(
    '/{message_id}',
    response_model=MessageModel,
    responses=docs.get__message)
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
    message = await Message.find_one(_find)
    # ? /plu/ral deletes the original message and replaces it silmultaneously
    # ? due to discord ratelimiting, the original message may be deleted before the proxy is created
    while message is None and _snowflake_to_age(message_id) < 5:
        await sleep(0.5)
        message = await Message.find_one(_find)

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
    response_model=MessageModel,
    responses=docs.post__message)
async def post__message(
    message: SendMessageModel,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    webhook = await DBWebhook.find_one({'_id': message.channel})

    if webhook is None:
        raise HTTPException(
            404, 'webhook not found; make sure at least one message is sent via discord message before using the API')

    if webhook.guild is None:
        raise HTTPException(
            400, 'invalid webhook url found, please send a message through the bot and try again')

    member = await Member.find_one({'_id': message.member})

    if member is None or token.user_id not in (await member.get_group()).accounts:
        raise HTTPException(404, 'member not found')

    if not await user_can_send(token.user_id, webhook.guild, message):
        raise HTTPException(
            403, 'you do not have permission to send messages to this channel')

    embed = MISSING
    if message.reference is not None:
        proxy_with_reply = await insert_reference_text(message, webhook.guild)

        if isinstance(proxy_with_reply, str):
            message.content = proxy_with_reply

        else:
            embed = proxy_with_reply

    avatar = None
    if member.avatar:
        image = await Image.find_one({'_id': member.avatar})
        if image is not None:
            avatar = (
                f'{project.base_url}/avatar/{image.id}.{image.extension}')

    async with ClientSession() as session:
        try:
            discord_webhook = DiscordWebhook.from_url(
                webhook.url, session=session)
        except InvalidArgument:
            raise HTTPException(
                400, 'invalid webhook url found, please send a message through the bot and try again')

        discord_message = await discord_webhook.send(
            allowed_mentions=AllowedMentions(
                everyone=False, roles=False, users=False),
            content=message.content,
            username=member.name,
            avatar_url=avatar,
            wait=True,
            thread=(
                Object(message.thread)
                if message.thread else
                MISSING),
            embed=embed
        )

    db_message = Message(
        original_id=None,
        proxy_id=discord_message.id,
        author_id=token.user_id
    )

    await db_message.save()

    return JSONResponse(
        content=db_message.model_dump_json(exclude={'id'})
    )
