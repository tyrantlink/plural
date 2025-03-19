from plural.db import ProxyMember, Group, Usergroup
from beanie import PydanticObjectId
from bson.errors import InvalidId

from plural.errors import InteractionError
from src.discord import Interaction


async def member_converter(
    interaction: Interaction,
    value: str,
    userproxy: bool = False
) -> ProxyMember | str:
    if (
        interaction.data.name == 'switch' and
        value.lower() in {'out', 'off', 'disable'}
    ):
        return 'out'

    try:
        parsed_value = PydanticObjectId(value)
    except InvalidId:
        raise InteractionError(
            'Invalid member id; Use the autocomplete') from None

    member = await ProxyMember.get(parsed_value)

    if member is None:
        raise InteractionError('Member not found')

    group = await member.get_group()

    usergroup = await Usergroup.get_by_user(interaction.author_id)

    if (
        usergroup.id not in group.accounts and
        interaction.author_id not in group.users
    ):
        raise InteractionError('Member not found')

    if userproxy and member.userproxy is None:
        raise InteractionError('Member does not have a userproxy')

    return member


async def group_converter(
    interaction: Interaction,
    value: str
) -> Group:
    try:
        parsed_value = PydanticObjectId(value)
    except InvalidId:
        raise InteractionError('Invalid id; Use the autocomplete') from None

    group = await Group.get(parsed_value)

    usergroup = await Usergroup.get_by_user(interaction.author_id)

    if (
        group is None or
        (usergroup.id not in group.accounts and
         interaction.author_id not in group.users)
    ):
        raise InteractionError('Group not found')

    return group


async def proxy_tag_converter(
    _interaction: Interaction,
    value: str
) -> int:
    try:
        return int(value)
    except ValueError:
        raise InteractionError(
            'Invalid proxy tag index; Use the autocomplete'
        ) from None
