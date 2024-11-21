from fastapi import HTTPException, Query, APIRouter
from src.core.models.message import MessageModel
from fastapi.responses import JSONResponse
from src.db import Message as DBMessage
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


@router.get(
    '/{message_id}',
    response_model=MessageModel,
    responses=docs.get__message)
async def get__message(
    message_id: int,
    only_check_existence: bool = Query(default=False),
    max_wait: int = Query(default=10, ge=0, le=10)
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


# @router.post(
#     '',
#     response_model=MessageModel,
#     responses=docs.post__message)
# async def post__message(
#     message: SendMessageModel,
#     token: TokenData = Security(api_key_validator)
# ) -> JSONResponse:
#     webhook = await DBWebhook.find_one({'_id': message.channel})

#     if webhook is None:
#         raise HTTPException(
#             404, 'webhook not found; make sure at least one message is sent via discord message before using the API')

#     if webhook.guild is None:
#         raise HTTPException(
#             400, 'invalid webhook url found, please send a message through the bot and try again')

#     member = await ProxyMember.find_one({'_id': message.member})

#     if member is None or token.user_id not in (await member.get_group()).accounts:
#         raise HTTPException(404, 'member not found')

#     # if not await user_can_send(token.user_id, webhook.guild, message):
#     #     raise HTTPException(
#     #         403, 'you do not have permission to send messages to this channel')

#     embed = MISSING
#     if message.reference is not None:
#         # await insert_reference_text(message, webhook.guild)
#         proxy_with_reply = ''

#         if isinstance(proxy_with_reply, str):
#             message.content = proxy_with_reply

#         else:
#             embed = proxy_with_reply

#     avatar = None
#     if member.avatar:
#         image = await Image.find_one({'_id': member.avatar})
#         if image is not None:
#             avatar = (
#                 f'{project.base_url}/avatar/{image.id}.{image.extension}')

#     async with ClientSession() as session:
#         try:
#             discord_webhook = DiscordWebhook.from_url(
#                 webhook.url, session=session)
#         except InvalidArgument:
#             raise HTTPException(
#                 400, 'invalid webhook url found, please send a message through the bot and try again')

#         discord_message = await discord_webhook.send(
#             allowed_mentions=AllowedMentions(
#                 everyone=False, roles=False, users=False),
#             content=message.content,
#             username=member.name,
#             avatar_url=avatar,
#             wait=True,
#             thread=(
#                 Object(message.thread)
#                 if message.thread else
#                 MISSING),
#             embed=embed
#         )

#     db_message = Message(
#         original_id=None,
#         proxy_id=discord_message.id,
#         author_id=token.user_id
#     )

#     await db_message.save()

#     return JSONResponse(
#         content=db_message.model_dump_json(exclude={'id'})
#     )
