from src.core.models.group import GroupModel, GroupUpdateModel, CreateGroupModel
from src.core.models.member import MemberModel, CreateMemberModel
from fastapi import HTTPException, APIRouter, Security, Query
from src.core.auth import api_key_validator, TokenData
from fastapi.responses import JSONResponse
from beanie import PydanticObjectId
from src.docs import group as docs
from src.db import Group, Image
from asyncio import gather

router = APIRouter(prefix='/group', tags=['Group'])


@router.get(
    '/{group_id}',
    response_model=GroupModel,
    responses=docs.get__group)
async def get__group(
    group_id: PydanticObjectId,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    group = await Group.find_one({'_id': group_id, 'accounts': token.user_id})

    if group is None:
        raise HTTPException(404, 'group not found')

    return JSONResponse(
        content=group.model_dump_json()
    )


@router.get(
    's',
    response_model=list[GroupModel],
    responses=docs.get__groups)
async def get__groups(
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    groups = await Group.find({'accounts': token.user_id}).to_list()

    return JSONResponse(
        content=[
            group.model_dump(mode='json')
            for group in
            groups
        ]
    )


@router.patch(
    '/{group_id}',
    response_model=GroupModel,
    responses=docs.patch__group)
async def patch__group(
    group_id: PydanticObjectId,
    patch: GroupUpdateModel,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    group = await Group.find_one({'_id': group_id, 'accounts': token.user_id})

    if group is None:
        raise HTTPException(404, 'group not found')

    for field in patch.model_fields_set:
        match field:
            case 'name':
                if await Group.find_one({'name': patch.name, 'accounts': token.user_id}) is not None:
                    raise HTTPException(
                        400, f'group {patch.name} already exists')

                group.name = patch.name
            case 'avatar':
                image = await Image.find_one({'_id': patch.avatar})

                if image is None:
                    raise HTTPException(404, 'avatar not found')

                group.avatar = patch.avatar
            case 'channels':
                group.channels = set(patch.channels)
            case 'tag':
                if (
                    patch.tag and
                    (
                        members_over_limit := [
                        member
                        for member in
                        await group.get_members()
                        if len(member.name+patch.tag) > 80
                        ]
                    )
                ):
                    raise HTTPException(
                        400, f'member(s) {", ".join([member.name for member in members_over_limit])} have a name and tag combined that exceeds 80 characters')
                group.tag = patch.tag
            case _:
                raise HTTPException(400, f'invalid field: {field}')

    await group.save_changes()

    return JSONResponse(
        content=group.model_dump_json()
    )


@router.post(
    '',
    response_model=GroupModel,
    responses=docs.post__group)
async def post__group(
    group: CreateGroupModel,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    if await Group.find_one({'name': group.name, 'accounts': token.user_id}) is not None:
        raise HTTPException(
            400, f'group {group.name} already exists')

    new_group = Group(
        name=group.name,
        accounts={token.user_id},
        avatar=group.avatar,
        channels=set(group.channels),
        tag=group.tag
    )

    await new_group.save()

    return JSONResponse(
        content=new_group.model_dump_json()
    )


@router.delete(
    '/{group_id}',
    responses=docs.delete__group)
async def delete__group(
    group_id: PydanticObjectId,
    delete_members: bool = Query(
        False,
        description='whether to delete all members of the group'),
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    group = await Group.find_one({'_id': group_id, 'accounts': token.user_id})
    tasks = []

    if group is None:
        raise HTTPException(404, 'group not found')

    response = {'deleted_group': group.name, 'deleted_members': []}

    if not delete_members and group.members:
        raise HTTPException(
            400, 'group has members; please delete or move all members first, or set param delete_members to true')

    if delete_members:
        for member in await group.get_members():
            tasks.append(member.delete())
            response['deleted_members'].append(member.name)

    tasks.append(group.delete())

    await gather(*tasks)

    return JSONResponse(
        content=response
    )


@router.get(
    '/{group_id}/members',
    response_model=list[GroupModel],
    responses=docs.get__group_members)
async def get__group_members(
    group_id: PydanticObjectId,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    group = await Group.find_one({'_id': group_id, 'accounts': token.user_id})

    if group is None:
        raise HTTPException(404, 'group not found')

    members = await group.get_members()

    return JSONResponse(
        content=[
            member.model_dump(mode='json')
            for member in
            members
        ]
    )


@router.get(
    '/{group_id}/member/{member_name}',
    response_model=MemberModel,
    responses=docs.get__group_member)
async def get__group_member(
    group_id: PydanticObjectId,
    member_name: str,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    group = await Group.find_one({'_id': group_id, 'accounts': token.user_id})

    if group is None:
        raise HTTPException(404, 'group not found')

    member = await group.get_member_by_name(member_name)

    if member is None:
        raise HTTPException(404, 'member not found')

    return JSONResponse(
        content=member.model_dump_json()
    )


@router.post(
    '/{group_id}/member',
    response_model=MemberModel,
    responses=docs.post__group_member)
async def post__group_member(
    group_id: PydanticObjectId,
    member: CreateMemberModel,
    token: TokenData = Security(api_key_validator)
) -> JSONResponse:
    group = await Group.find_one({'_id': group_id, 'accounts': token.user_id})

    if group is None:
        raise HTTPException(404, 'group not found')

    if await group.get_member_by_name(member.name) is not None:
        raise HTTPException(
            400, f'member {member.name} already exists')

    if group.tag and (len_sum := len(member.name+group.tag)) > 80:
        raise HTTPException(
            400, f'name and group tag combined must be less than 80 characters ({len_sum}/80)')

    new_member = await group.add_member(
        name=member.name,
        save=False
    )

    new_member.avatar = member.avatar
    new_member.proxy_tags = member.proxy_tags

    await new_member.save()

    return JSONResponse(
        content=new_member.model_dump_json()
    )
