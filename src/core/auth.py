from src.discord.models import Interaction, ApplicationIntegrationType
from fastapi import Security, HTTPException, Request, Header
from src.helpers import decode_b66, BASE66CHARS, TTLSet
from fastapi.security.api_key import APIKeyHeader
from concurrent.futures import ThreadPoolExecutor
from nacl.exceptions import BadSignatureError
from typing import NamedTuple, Annotated
from nacl.signing import VerifyKey
from asyncio import get_event_loop
from src.db import ApiKey, Member
from src.models import project
from re import match, escape
from bcrypt import checkpw
from json import loads


TOKEN_MATCH_PATTERN = ''.join([
    f'^([{escape(BASE66CHARS)}]', r'{1,16})\.',
    f'([{escape(BASE66CHARS)}]', r'{5,8})\.',
    f'([{escape(BASE66CHARS)}]', r'{20,27})$'])

API_KEY = APIKeyHeader(name='token')


class TokenData(NamedTuple):
    user_id: int
    timestamp: int
    key: int


VALID_TOKENS = TTLSet[str]()


async def acheckpw(password: str, hashed: str) -> bool:
    with ThreadPoolExecutor() as executor:
        result = await get_event_loop(
        ).run_in_executor(
            executor,
            lambda: checkpw(password.encode(), hashed.encode())
        )
    return result


async def api_key_validator(api_key: str = Security(API_KEY)) -> TokenData:
    regex = match(TOKEN_MATCH_PATTERN, api_key)

    if regex is None:
        raise HTTPException(400, 'api key not in correct format!')

    token = TokenData(
        user_id=decode_b66(regex.group(1)),
        timestamp=decode_b66(regex.group(2)),
        key=decode_b66(regex.group(3)))

    key_doc = await ApiKey.find_one({'_id': token.user_id})

    if key_doc is None or key_doc.token is None:
        raise HTTPException(400, 'api key not found!')

    if not key_doc.token in VALID_TOKENS:
        if not await acheckpw(api_key, key_doc.token):
            raise HTTPException(400, 'api key invalid!')

        VALID_TOKENS.add(key_doc.token)

    return token


async def discord_key_validator(
    request: Request,
    x_signature_ed25519: Annotated[str, Header()],
    x_signature_timestamp: Annotated[str, Header()],
) -> bool:
    try:
        request_body = (await request.body()).decode()
        interaction = Interaction.model_validate_json(request_body)
    except Exception:
        raise HTTPException(400, 'Invalid request body')

    member = None
    match interaction.application_id:
        case project.application_id:
            verify_key = VerifyKey(bytes.fromhex(project.bot_public_key))
        case _:
            member = await Member.find_one({'userproxy.bot_id': interaction.application_id})

            if member is None or member.userproxy is None:
                raise HTTPException(400, 'Invalid application id')

            verify_key = VerifyKey(bytes.fromhex(member.userproxy.public_key))

    try:
        verify_key.verify(
            f'{x_signature_timestamp}{request_body}'.encode(),
            bytes.fromhex(x_signature_ed25519)
        )
    except BadSignatureError:
        raise HTTPException(401, 'Invalid request signature')

    if (  # ? always accept pings and interactions directed at the main bot
        interaction.type.value == 1 or
        interaction.application_id == project.application_id
    ):
        return True

    assert member is not None

    user_id = (
        int(
            interaction.authorizing_integration_owners.get(
                ApplicationIntegrationType.USER_INSTALL, 0)
        ) if interaction.authorizing_integration_owners is not None else
        None
    )

    if user_id is None or user_id not in (await member.get_group()).accounts:
        raise HTTPException(401, 'Invalid user id')

    return True


async def gateway_key_validator(
    request: Request,
    x_signature_ed25519: Annotated[str, Header()],
    x_signature_timestamp: Annotated[str, Header()],
) -> bool:
    try:
        request_body = (await request.body()).decode()
    except Exception:
        raise HTTPException(400, 'Invalid request body')

    verify_key = VerifyKey(bytes.fromhex(project.gateway_key))

    try:
        verify_key.verify(
            f'{x_signature_timestamp}{request_body}'.encode(),
            bytes.fromhex(x_signature_ed25519)
        )
    except BadSignatureError:
        raise HTTPException(401, 'Invalid request signature')

    return True
