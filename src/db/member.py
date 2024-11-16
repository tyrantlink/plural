from __future__ import annotations
from .helpers import avatar_setter, avatar_deleter, ImageId
from pydantic import Field, model_validator, BaseModel
from typing import Annotated, TYPE_CHECKING, Any
from beanie import Document, PydanticObjectId
from datetime import timedelta
from re import sub, IGNORECASE


if TYPE_CHECKING:
    from src.db.group import Group


class ProxyMember(Document):
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

    @model_validator(mode='before')
    def _handle_avatar(cls, values: dict[Any, Any]) -> dict[Any, Any]:
        if isinstance((avatar := values.get('avatar', None)), bytes):
            values['avatar'] = ImageId.validate(avatar)
        return values

    class Settings:
        name = 'members'
        use_cache = True
        validate_on_save = True
        use_state_management = True
        cache_expiration_time = timedelta(seconds=5)
        indexes = ['userproxy.bot_id']
        bson_encoders = {ImageId: bytes}

    class ProxyTag(BaseModel):
        prefix: str = Field(
            '',
            max_length=50,
            description='tag must have a prefix or suffix')
        suffix: str = Field(
            '',
            max_length=50,
            description='tag must have a prefix or suffix')
        regex: bool = False
        case_sensitive: bool = False

        @model_validator(mode='after')
        def check_prefix_and_suffix(cls, value):
            if not value.prefix and not value.suffix:
                raise ValueError(
                    'At least one of prefix or suffix must be non-empty')

            return value

    class UserProxy(BaseModel):
        bot_id: int = Field(description='bot id')
        public_key: str = Field(description='the userproxy public key')
        token: str | None = Field(
            None,
            description='the bot token, only stored when autosyncing is enabled')
        command: str | None = Field(
            'proxy', description='name of the proxy command')

        @property
        def autosync(self) -> bool:
            return self.token is not None

    id: PydanticObjectId = Field(  # type: ignore
        default_factory=PydanticObjectId)
    name: str = Field(
        description='the name of the member',
        min_length=1, max_length=80
    )
    avatar: ImageId | None = Field(
        None,
        description='the avatar uuid of the member; overrides the group avatar'
    )
    proxy_tags: Annotated[list[ProxyTag], Field(max_length=15)] = Field(
        [],
        description='proxy tags for the member'
    )
    userproxy: ProxyMember.UserProxy | None = Field(
        None,
        description='the userproxy information'
    )

    @property
    def avatar_url(self) -> str | None:
        from src.models import project

        if self.avatar is None:
            return None

        return f'{project.images.base_url}/{self.id}/{self.avatar.id}.{self.avatar.extension.name.lower()}'

    async def get_group(self) -> Group:
        from src.db.group import Group

        group = await Group.find_one({'members': self.id})

        if group is None:
            raise ValueError(f'member {self.id} is not in any group')

        return group

    async def set_avatar(self, url: str) -> None:
        await avatar_setter(self, url)

    async def delete_avatar(self) -> None:
        await avatar_deleter(self)
