from datetime import timedelta
from typing import NamedTuple

from fastapi import APIRouter, Security, Depends, Response
from beanie import PydanticObjectId
from orjson import dumps

from plural.errors import NotFound, HTTPException
from plural.db import ProxyMember
from plural.otel import cx

from src.core.auth import TokenData, api_key_validator, authorized_member
from src.core.ratelimit import ratelimit
from src.models import UserproxySync
from src.core.models import env
from src.core.route import name
from src.discord import User

from src.models import MemberModel

from src.commands.helpers import make_json_safe


router = APIRouter(prefix='/members', tags=['Members'])


class FakeInteraction(NamedTuple):
    author_id: int
    author_name: str


@router.get(
    '/{member_id}',
    description="""
        Get a member by id

    Requires authorized user""",
    responses={
        200: {
            'description': 'Member found',
            'model': MemberModel,
            'content': {
                'application/json': {
                    'examples': {
                        'Member with Userproxy': {'value': {
                            'id': '67cab2a55f8b2e7fd3d27d0c',
                            'name': 'steve',
                            'meta': '',
                            'pronouns': 'any/all',
                            'bio': 'example bio',
                            'birthday': '01/01/2000',
                            'color': 16777065,
                            'avatar': 'f873c5cff5608ff4952cfe8b80f1a86c',
                            'simply_plural_id': None,
                            'proxy_tags': [
                                {
                                    "id": "67cab28fe3188a0a7807c8fd",
                                    "prefix": "s;",
                                    "suffix": "",
                                    "regex": False,
                                    "case_sensitive": False,
                                    "avatar": None
                                },
                                {
                                    "id": "67cab28fe3188a0a7807c8fe",
                                    "prefix": "",
                                    "suffix": "--steve",
                                    "regex": False,
                                    "case_sensitive": False,
                                    "avatar": None
                                }
                            ],
                            'userproxy': {
                                'bot_id': '1297857704512978984',
                                'public_key': '267b5eb2ebdbe0620160b0cd99630420cce9f1fa271feaf16bee8a20988dc682',
                                'token': 'bot token',
                                'command': 'st',
                                'guilds': [
                                    '844127424526680084'
                                ]
                            }
                        }},
                        'Member without Userproxy': {'value': {
                            'id': '67cab2a55f8b2e7fd3d27d0c',
                            'name': 'steve',
                            'meta': '',
                            'pronouns': 'any/all',
                            'bio': 'example bio',
                            'birthday': '01/01/2000',
                            'color': 16777065,
                            'avatar': 'f873c5cff5608ff4952cfe8b80f1a86c',
                            'simply_plural_id': None,
                            'proxy_tags': [
                                {
                                    "id": "67cab28fe3188a0a7807c8fd",
                                    "prefix": "s;",
                                    "suffix": "",
                                    "regex": False,
                                    "case_sensitive": False,
                                    "avatar": None
                                },
                                {
                                    "id": "67cab28fe3188a0a7807c8fe",
                                    "prefix": "",
                                    "suffix": "--steve",
                                    "regex": False,
                                    "case_sensitive": False,
                                    "avatar": None
                                }
                            ],
                            'userproxy': None
                        }}
                    }
                }
            }
        },
        403: {
            'description': 'Application not authorized to access this member'
        },
        404: {
            'description': 'Member not found'
        }
    })
@name('/members/:id')
@ratelimit(5, timedelta(seconds=30), ['member_id'])
async def get__member(
    member_id: PydanticObjectId,  # noqa: ARG001
    token: TokenData = Security(api_key_validator),  # noqa: B008
    member: ProxyMember = Depends(authorized_member)  # noqa: B008
) -> Response:
    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps(make_json_safe(MemberModel.from_member(
            await (await member.get_group()).get_usergroup(),
            member,
            token
        ).model_dump()))
    )


@router.post(
    '/{member_id}/userproxy/sync',
    status_code=204,
    description="""
        Sync a member's userproxy

    Requires authorized user""",
    responses={
        204: {
            'description': 'Userproxy synced',
            'content': None
        },
        400: {
            'description': 'Discord error',
            'content': {
                'application/json': {
                    'examples': {
                        'Discord error': {'value': {
                            'detail': {
                                'discord_error': {
                                    'message': 'Invalid Form Body', 'code': 50035,
                                    'errors': {
                                        'username': {
                                            '_errors': [
                                                {
                                                    'code': 'USERNAME_RATE_LIMIT',
                                                    'message': 'You are changing your username or Discord Tag too fast. Try again later.'
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        }}
                    }
                }
            }
        },
        403: {
            'description': 'Application not authorized to access this member'
        },
        404: {
            'description': 'Member not found or user not found'
        },
    })
@name('/members/:id/userproxy/sync')
@ratelimit(1, timedelta(seconds=30), ['member_id'])
async def post__member_userproxy_sync(
    member_id: PydanticObjectId,  # noqa: ARG001
    body: UserproxySync,
    token: TokenData = Security(api_key_validator),  # noqa: ARG001,B008
    member: ProxyMember = Depends(authorized_member)  # noqa: B008
) -> Response:
    from src.commands.userproxy import _userproxy_sync

    cx().set_attribute('patch_filter', list(body.patch_filter))

    try:
        user = await User.fetch(
            body.author_id,
            env.bot_token)
    except NotFound:
        return Response(status_code=404)

    try:
        await _userproxy_sync(
            FakeInteraction(
                author_id=body.author_id,
                author_name=user.username),
            member,
            body.patch_filter,
            silent=True
        )
    except HTTPException as e:
        return Response(
            status_code=400,
            media_type='application/json',
            content=dumps({
                'detail': {
                    'discord_error': e.detail or None
                }
            })
        )

    return Response(status_code=(
        204
    ))
