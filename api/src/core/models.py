from __future__ import annotations
from pydantic import GetJsonSchemaHandler, GetCoreSchemaHandler
from typing import TypeVar, Union, Any, Literal, TYPE_CHECKING
from pydantic_core import CoreSchema, core_schema
from pydantic import BaseModel
from base64 import b64decode
from tomllib import loads
from os import environ

if TYPE_CHECKING:
    from pydantic.json_schema import JsonSchemaValue


LEGACY_FOOTERS = {
    'userproxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural',
    'a plural proxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
}
USERPROXY_FOOTER = '\n\na plural proxy for @{username} powered by /plu/ral\nhttps://plural.gg'
USERPROXY_FOOTER_LIMIT = 400 - len(USERPROXY_FOOTER.format(username='*' * 32))


class Env(BaseModel):
    bot_token: str
    redis_url: str
    logfire_token: str
    domain: str
    dev: bool

    @property
    def application_id(self) -> int:
        if getattr(self, '_application_id', None) is None:
            self._application_id = loads(
                b64decode(
                    self.bot_token.split('.')[0] + '=='
                ).decode()
            )['id']

        return self._application_id

    @property
    def public_key(self) -> str:
        if getattr(self, '_public_key', None) is None:
            ...

        return self._public_key


class _MissingType:
    def __bool__(self) -> Literal[False]:
        return False

    def __repr__(self) -> str:
        return "MISSING"

    def __copy__(self) -> _MissingType:
        return self

    def __deepcopy__(
        self,
        _: Any  # noqa: ANN401
    ) -> _MissingType:
        return self

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,  # noqa: ANN401
        _handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.none_schema(),
            python_schema=core_schema.is_instance_schema(cls),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "null"}


MISSING = _MissingType()

INSTANCE = hex(id(MISSING))[2:]

T = TypeVar('T')
MissingOr = Union[T, _MissingType]
MissingNoneOr = Union[T, None, _MissingType]

env = Env.model_validate({
    'bot_token': environ.get('BOT_TOKEN', MISSING),
    'redis_url': environ.get('REDIS_URL', MISSING),
    'domain': environ.get('DOMAIN', MISSING),
    'dev': environ.get('DEV', '1') == '1'
})

print(env)
