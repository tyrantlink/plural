from typing import TYPE_CHECKING, overload
from .member import MemberManageView
from .group import GroupManageView

if TYPE_CHECKING:
    from src.db import Group, Member
    from src.client import Client


@overload
async def get_manage_view(
    client: Client,
    group: Group,
    member: Member,
    **kwargs
) -> MemberManageView:
    ...


@overload
async def get_manage_view(
    client: Client,
    group: Group,
    member: None = None,
    **kwargs
) -> GroupManageView:
    ...


async def get_manage_view(
    client: Client,
    group: Group,
    member: Member | None = None,
    **kwargs
) -> MemberManageView | GroupManageView:
    if member is not None:
        return MemberManageView(client, group, member, **kwargs)

    return GroupManageView(client, group, member, **kwargs)
