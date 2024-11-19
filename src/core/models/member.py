from .base import excluded_model, patch_model
from pydantic import BaseModel, Field
from beanie import PydanticObjectId
from typing import TYPE_CHECKING
from src.db import ProxyMember


class MemberGet(excluded_model(
    original_model=ProxyMember,
    exclude_fields=[
        '_id',
        'revision_id'
    ]
)):
    ...


class MemberPatch(patch_model(
    original_model=ProxyMember,
    include_fields=[
        'name',
        'group',
        'proxy_tags'
    ]
)):
    if TYPE_CHECKING:
        name: str
        group: PydanticObjectId
        proxy_tags: list[ProxyMember.ProxyTag]


class MemberPost(BaseModel):
    ...
