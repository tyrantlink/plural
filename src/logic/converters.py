from src.discord import Interaction, ApplicationCommandInteractionDataOption
from src.errors import ConversionError
from src.db import ProxyMember, Group
from beanie import PydanticObjectId
from bson.errors import InvalidId


def _try_object_id(value: str) -> PydanticObjectId | None:
    try:
        return PydanticObjectId(value)
    except InvalidId:
        return None


async def member_converter(
    interaction: Interaction,
    options: dict[str, ApplicationCommandInteractionDataOption],
    value: str
) -> ProxyMember:
    parsed_value = _try_object_id(value)

    member, group = None, None

    group_option = options.get('group')

    if parsed_value is not None:
        member = await ProxyMember.get(parsed_value)

    if member is None:
        group = await group_converter(
            interaction,
            options,
            str(group_option.value) if group_option is not None else 'default')

        member = await group.get_member_by_name((
            split[1]
            if len(split := value.split('] ', 1)) == 2
            else value
        ))

    if member is None:
        raise ConversionError('member not found')

    if group is None:
        group = await member.get_group()

    if interaction.author_id not in group.accounts:
        raise ConversionError('member not found')

    return member


async def group_converter(
    interaction: Interaction,
    _options: dict[str, ApplicationCommandInteractionDataOption],
    value: str
) -> Group:
    parsed_value = _try_object_id(value)

    group = None

    if parsed_value is not None:
        group = await Group.get(parsed_value)

    if group is None:
        group = await Group.find_one(
            {'accounts': interaction.author_id, 'name': value})

    if group is None and value == 'default':
        group = await Group(
            accounts={interaction.author_id},
            name='default',
            avatar=None,
            tag=None
        ).save()

    if group is None or interaction.author_id not in group.accounts:
        raise ConversionError('group not found')

    return group
