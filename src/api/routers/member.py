from src.api.models.member import MemberModel, MemberUpdateModel
from src.api.auth import api_key_validator, TokenData
from fastapi import HTTPException, Security
from fastapi.responses import JSONResponse
from src.api.docs import member as docs
from beanie import PydanticObjectId
from fastapi import APIRouter
from src.db import Member

router = APIRouter(prefix='/member', tags=['Member'])


@router.get(
    '/{member_id}',
    response_model=MemberModel,
    responses=docs.get__member)
async def get__member(
    member_id: PydanticObjectId,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    member = await Member.find_one({'_id': member_id})

    if member is None or token.user_id not in (await member.get_group()).accounts:
        raise HTTPException(404, 'member not found')

    return JSONResponse(
        content=member.model_dump_json(exclude={'id'})
    )


@router.patch(
    '/{member_id}',
    response_model=MemberModel,
    responses=docs.patch__member)
async def patch__member(
    member_id: PydanticObjectId,
    patch: MemberUpdateModel,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    member = await Member.find_one({'_id': member_id})

    if member is None or token.user_id not in (await member.get_group()).accounts:
        raise HTTPException(404, 'member not found')

    for field in patch.model_fields_set:
        match field:
            case 'name':
                member.name = patch.name
            case 'avatar':
                member.avatar = patch.avatar
            case 'proxy_tags':
                member.proxy_tags = patch.proxy_tags
            case _:
                raise HTTPException(400, f'invalid field: {field}')

    await member.save_changes()

    return JSONResponse(
        content=member.model_dump_json(exclude={'id'})
    )
