from __future__ import annotations
from typing import Annotated, TYPE_CHECKING, Any
from src.models import USERPROXY_FOOTER_LIMIT
from beanie import Document, PydanticObjectId
from pydantic import Field, model_validator
from re import sub, IGNORECASE
from .models import ProxyTag


if TYPE_CHECKING:
    from src.db.group import Group
    from src.db.userproxy import UserProxy


class Member(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @model_validator(mode='before')
    def _handle_clyde(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        if (name := values.get('name', None)) is None:
            return values

        # ? just stolen from pluralkit https://github.com/PluralKit/PluralKit/blob/214a6d5a4933b975068b0272c98d178a47b487d5/src/pluralkit/bot/proxy.py#L62
        values['name'] = sub(
            '(c)(lyde)',
            '\\1\u200A\\2',
            name,
            flags=IGNORECASE
        )
        return values

    class Settings:
        name = 'members'
        validate_on_save = True
        use_state_management = True

    id: PydanticObjectId = Field(default_factory=PydanticObjectId)
    name: str = Field(
        description='the name of the member',
        min_length=1, max_length=50
    )
    description: str | None = Field(
        None,
        description='the description of the member, only used for userproxies',
        max_length=USERPROXY_FOOTER_LIMIT
    )
    avatar: PydanticObjectId | None = Field(
        None,
        description='the avatar uuid of the member; overrides the group avatar'
    )
    proxy_tags: Annotated[list[ProxyTag], Field(max_length=15)] = Field(
        [],
        description='proxy tags for the member'
    )

    async def get_group(self) -> Group:
        from src.db.group import Group

        group = await Group.find_one({'members': self.id})

        if group is None:
            raise ValueError(f'member {self.id} is not in any group')

        return group

    async def get_userproxy(self) -> UserProxy | None:
        from src.db.userproxy import UserProxy

        return await UserProxy.find_one({'member': self.id})

    async def get_avatar_url(self) -> str | None:
        from src.models import project
        from src.db.image import Image
        from src.db.models import DatalessImage

        if self.avatar is None or (
                image := await Image.find_one(
                    {'_id': self.avatar},
                    projection_model=DatalessImage
                )
        ) is None:
            return None

        return f'{project.base_url}/avatar/{image.id}.{image.extension}'
