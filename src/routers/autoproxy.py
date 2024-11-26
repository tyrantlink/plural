from src.core.models import AutoProxyResponse, AutoProxyPatch, AutoProxyPost
from src.core.auth import api_key_validator, TokenData, Security
from fastapi import HTTPException, APIRouter, Response
from fastapi.responses import JSONResponse
from src.docs import autoproxy as docs
from typing import Literal
from src.db import Latch


router = APIRouter(prefix='/autoproxy', tags=['Autoproxy'])


@router.get(
    '/{guild_id}',
    response_model=AutoProxyResponse,
    responses=docs.get__autoproxy)
async def get__autoproxy(
    guild_id: int | Literal['global'],
    token_data: TokenData = Security(api_key_validator)
) -> JSONResponse:
    """
    get your autoproxy
    """

    guild = None if guild_id == 'global' else guild_id

    latch = await Latch.find_one(
        {'user': token_data.user_id, 'guild': guild}
    )

    if latch is None:
        raise HTTPException(status_code=404, detail='autoproxy not found')

    return JSONResponse(
        content=AutoProxyResponse.model_validate(
            latch.model_dump(exclude={'_id'})
        ).model_dump(mode='json')
    )


@router.patch(
    '/{guild_id}',
    response_model=AutoProxyResponse,
    responses=docs.get__autoproxy)
async def patch__autoproxy(
    guild_id: int | Literal['global'],
    patch: AutoProxyPatch,
    token_data: TokenData = Security(api_key_validator)
) -> JSONResponse:
    """
    modify your autoproxy
    """

    guild = None if guild_id == 'global' else guild_id

    latch = await Latch.find_one(
        {'user': token_data.user_id, 'guild': guild}
    )

    if latch is None:
        raise HTTPException(status_code=404, detail='autoproxy not found')

    for field in patch.model_fields_set:
        match field:
            case 'enabled' | 'fronting' | 'member':
                pass
            case _:
                # ? pydantic should catch this, but just in case
                raise HTTPException(status_code=400)

        setattr(latch, field, getattr(patch, field))

    await latch.save()

    return JSONResponse(
        content=AutoProxyResponse.model_validate(
            latch.model_dump(exclude={'_id'})
        ).model_dump(mode='json')
    )


@router.post(
    '',
    response_model=AutoProxyResponse,
    responses=docs.post__autoproxy)
async def post__autoproxy(
    post: AutoProxyPost,
    token_data: TokenData = Security(api_key_validator)
) -> JSONResponse:
    """
    create a new autoproxy
    """

    latch = await Latch.find_one(
        {'user': token_data.user_id, 'guild': post.guild}
    )

    if latch is not None:
        raise HTTPException(status_code=400, detail='autoproxy already exists')

    latch = Latch(
        user=token_data.user_id,
        guild=post.guild,
        enabled=post.enabled,
        fronting=post.fronting,
        member=post.member
    )

    await latch.save()

    return JSONResponse(
        content=AutoProxyResponse.model_validate(
            latch.model_dump(exclude={'_id'})
        ).model_dump(mode='json')
    )


@router.put(
    '',
    response_model=AutoProxyResponse,
    responses=docs.put__autoproxy)
async def put__autoproxy(
    put: AutoProxyPost,
    token_data: TokenData = Security(api_key_validator)
) -> JSONResponse:
    """
    create or replace your autoproxy
    """

    latch = Latch(
        user=token_data.user_id,
        guild=put.guild,
        enabled=put.enabled,
        fronting=put.fronting,
        member=put.member
    )

    await latch.save()

    return JSONResponse(
        content=AutoProxyResponse.model_validate(
            latch.model_dump(exclude={'_id'})
        ).model_dump(mode='json')
    )


@router.delete(
    '/{guild_id}',
    status_code=204)
async def delete__autoproxy(
    guild_id: int | Literal['global'],
    token_data: TokenData = Security(api_key_validator)
) -> Response:
    """
    delete your autoproxy
    """

    guild = None if guild_id == 'global' else guild_id

    latch = await Latch.find_one(
        {'user': token_data.user_id, 'guild': guild}
    )

    if latch is None:
        raise HTTPException(status_code=404, detail='autoproxy not found')

    await latch.delete()

    return Response(status_code=204)
