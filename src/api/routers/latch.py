from src.api.models.latch import LatchModel, LatchUpdateModel
from src.api.auth import api_key_validator, TokenData
from fastapi import HTTPException, Security
from fastapi.responses import JSONResponse
from src.api.docs import latch as docs
from beanie import PydanticObjectId
from bson.errors import InvalidId
from src.db import Latch, Member
from fastapi import APIRouter

router = APIRouter(prefix='/latch', tags=['Latch'])


@router.get(
    '/{guild_id}',
    response_model=LatchModel,
    responses=docs.get__latch)
async def get__latch(
    guild_id: int,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    latch = await Latch.find_one({'user': token.user_id, 'guild': guild_id})

    if latch is None:
        raise HTTPException(404, 'latch not found')

    return JSONResponse(
        content=latch.model_dump_json(exclude={'id'})
    )


@router.patch(
    '/{guild_id}',
    response_model=LatchModel,
    responses=docs.patch__latch)
async def patch__latch(
    guild_id: int,
    patch: LatchUpdateModel,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    latch = await Latch.find_one({'user': token.user_id, 'guild': guild_id})

    if latch is None:
        raise HTTPException(404, 'latch not found')

    latch.enabled = (
        enabled
        if (
            (enabled := patch.enabled) is not None and
            isinstance(enabled, bool)
        )
        else latch.enabled

    )

    if (
        (member_id := patch.member) is not None and
        isinstance(member_id, str)
    ):
        try:
            member_id = PydanticObjectId(member_id)
        except InvalidId:
            raise HTTPException(400, 'invalid member id')

        member = await Member.find_one({'_id': member_id})

        if member is None:
            raise HTTPException(404, 'member not found')

        if token.user_id not in (await member.get_group()).accounts:
            # ? be vauge to prevent user enumeration
            raise HTTPException(404, 'member not found')

        latch.member = member_id

    await latch.save_changes()

    return JSONResponse(
        content=latch.model_dump_json(exclude={'id'})
    )
