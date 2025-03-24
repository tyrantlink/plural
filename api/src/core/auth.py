from concurrent.futures import ThreadPoolExecutor
from asyncio import get_event_loop
from dataclasses import dataclass
from typing import Annotated
from re import match, escape
from hashlib import sha256

from fastapi import Security, HTTPException, Request, Header
from fastapi.security.api_key import APIKeyHeader
from nacl.exceptions import BadSignatureError
from pydantic_core import ValidationError
from nacl.signing import VerifyKey
from bcrypt import checkpw
from orjson import loads

from plural.db import ProxyMember, Usergroup, Application, redis
from plural.crypto import decode_b66, BASE66CHARS
from beanie import PydanticObjectId
from plural.otel import span

from src.discord import Interaction, ApplicationIntegrationType, WebhookEvent
from src.core.models import env


TOKEN_MATCH_PATTERN = ''.join([
    f'^([{escape(BASE66CHARS)}]', r'{1,16})\.',
    f'([{escape(BASE66CHARS)}]', r'{5,8})\.',
    f'([{escape(BASE66CHARS)}]', r'{20,27})$'])

API_KEY = APIKeyHeader(
    name='Authorization',
    scheme_name='Application Token',
    description='Use `/api` from /plu/ral to get a token'
)

INVALID_TOKEN = HTTPException(400, {
    'detail': {
        'loc': ['header', 'Authorization'],
        'msg': 'Invalid token',
        'type': 'value_error'
    }
})


@dataclass
class TokenData:
    app_id: PydanticObjectId
    timestamp: int
    key: int

    @property
    def redis_key(self) -> str:
        return 'token:' + sha256(
            f'{int.from_bytes(self.app_id.binary)}.{self.timestamp}'.encode()
        ).hexdigest()

    @property
    def application(self) -> Application:
        if not hasattr(self, '_application'):
            raise AttributeError('Application not set')

        return self._application


async def acheckpw(password: str, hashed: str) -> bool:
    with ThreadPoolExecutor() as executor:
        return await get_event_loop(
        ).run_in_executor(
            executor,
            lambda: checkpw(password.encode(), hashed.encode())
        )


async def api_key_validator(token: str = Security(API_KEY)) -> TokenData:
    regex = match(TOKEN_MATCH_PATTERN, token)

    if regex is None:
        raise INVALID_TOKEN

    token_data = TokenData(
        app_id=PydanticObjectId(decode_b66(regex.group(1)).to_bytes(12)),
        timestamp=decode_b66(regex.group(2)),
        key=decode_b66(regex.group(3))
    )

    if (application := await Application.get(token_data.app_id)) is None:
        raise INVALID_TOKEN

    token_data._application = application

    if await redis.get(token_data.redis_key):
        # ? token already validated, bcrypt is slow
        return token_data

    if not await acheckpw(token, application.token):
        raise INVALID_TOKEN

    await redis.set(token_data.redis_key, '1', ex=3600)

    return token_data


async def _discord_key_validator(
    request: Request,
    x_signature_ed25519: Annotated[str, Header()],
    x_signature_timestamp: Annotated[str, Header()],
) -> bool:
    try:
        request_body = (await request.body()).decode()
    except Exception as e:
        raise HTTPException(400, 'Invalid request body') from e

    try:
        application_id = int(loads(request_body)['application_id'])
    except Exception as e:
        raise HTTPException(400, 'Invalid request body') from e

    member = None
    match application_id:
        case env.application_id:
            verify_key = VerifyKey(bytes.fromhex(env.public_key))
        case _:
            member = await ProxyMember.find_one({
                'userproxy.bot_id': application_id
            })

            if not isinstance(member, ProxyMember) or member.userproxy is None:
                raise HTTPException(400, 'Invalid application id')

            verify_key = VerifyKey(bytes.fromhex(member.userproxy.public_key))

    verify_key.verify(
        f'{x_signature_timestamp}{request_body}'.encode(),
        bytes.fromhex(x_signature_ed25519))

    try:
        WebhookEvent.model_validate_json(request_body)
        return True
    except ValidationError:
        pass

    try:
        interaction = Interaction.model_validate_json(request_body)
    except ValidationError as invalid:
        raise HTTPException(
            400, 'Invalid interaction or webhook event'
        ) from invalid

    if (  # ? always accept pings and interactions directed at the main bot
        interaction.type.value == 1 or
        interaction.application_id == env.application_id
    ):
        return True

    if member is None:
        raise HTTPException(400, 'Invalid application id')

    user_id = (
        int(
            interaction.authorizing_integration_owners.get(
                ApplicationIntegrationType.USER_INSTALL, 0)
        ) if interaction.authorizing_integration_owners is not None else
        None
    )

    if user_id is None:
        raise HTTPException(400, 'Invalid user id')

    usergroup = await Usergroup.get_by_user(user_id)
    group = await member.get_group()

    if (
        usergroup.id not in group.accounts and
        user_id not in group.users
    ):
        raise HTTPException(401, 'Invalid user id')

    return True


async def discord_key_validator(
    request: Request,
    x_signature_ed25519: Annotated[str, Header()],
    x_signature_timestamp: Annotated[str, Header()],
) -> bool:
    try:
        return await _discord_key_validator(
            request,
            x_signature_ed25519,
            x_signature_timestamp)
    except BadSignatureError as e:
        raise HTTPException(
            401, 'Invalid request signature'
        ) from e
    except Exception as e:
        with span('discord validation error') as current_span:
            current_span.record_exception(e)
            raise e
