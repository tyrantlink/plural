from hashlib import sha256

from fastapi import APIRouter, Security, Response
from orjson import dumps

from plural.db import ProxyMember, Usergroup, Group

from src.core.auth import selfhosting_key_validator
from src.core.route import name

from src.models import UserProxyModel


router = APIRouter(prefix='', include_in_schema=False)


@router.get('/userproxies')
@name('/userproxies')
async def get__user_userproxies(
    usergroup: Usergroup = Security(selfhosting_key_validator),  # noqa: B008
    version: str | None = None
) -> Response:
    if version and version == usergroup.data.userproxy_version:
        return Response(status_code=304)

    members = await Group.aggregate([
        {'$match': {'account': usergroup.id}},
        {'$unwind': '$members'},
        {'$lookup': {
            'from': 'members',
            'localField': 'members',
            'foreignField': '_id',
            'as': 'member_details'}},
        {'$unwind': '$member_details'},
        {'$replaceRoot': {'newRoot': '$member_details'}},
        {'$match': {'userproxy': {'$ne': None}}},
        {'$sort': {'_id': 1}}
    ], projection_model=ProxyMember).to_list()

    value = dumps([
        UserProxyModel.from_member(
            member
        ).model_dump(mode='json')
        for member in members
    ])

    usergroup.data.userproxy_version = sha256(value).hexdigest()
    await usergroup.save()

    return Response(
        status_code=200,
        media_type='application/json',
        headers={
            'Etag': usergroup.data.userproxy_version},
        content=value
    )
