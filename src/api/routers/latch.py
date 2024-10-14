from src.api.models.latch import LatchModel, LatchUpdateModel
from src.api.auth import api_key_validator, TokenData
from fastapi import HTTPException, Security
from fastapi.responses import JSONResponse
from src.api.docs import latch as docs
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

    for field in patch.model_fields_set:
        match field:
            case 'enabled':
                latch.enabled = patch.enabled
            case 'member':
                member = await Member.find_one({'_id': patch.member})

                if member is None or token.user_id not in (await member.get_group()).accounts:
                    # ? be vauge to prevent user enumeration
                    raise HTTPException(404, 'member not found')

                latch.member = patch.member
            case _:
                raise HTTPException(400, f'invalid field: {field}')

    await latch.save_changes()

    return JSONResponse(
        content=latch.model_dump_json(exclude={'id'})
    )