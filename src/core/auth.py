from src.helpers import decode_b66, BASE66CHARS, TTLSet
from fastapi.security.api_key import APIKeyHeader
from concurrent.futures import ThreadPoolExecutor
from fastapi import Security, HTTPException
from asyncio import get_event_loop
from typing import NamedTuple
from re import match, escape
from bcrypt import checkpw
from src.db import ApiKey


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
