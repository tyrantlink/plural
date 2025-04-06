from __future__ import annotations

from plural.env import Env as BaseEnv
from plural.otel import span


LEGACY_FOOTERS = {
    'a plural proxy for @{username} powered by /plu/ral\nhttps://plural.gg',
    'userproxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural',
    'a plural proxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
}
USERPROXY_FOOTER = '\n\na plural proxy for @{username}\npowered by /plu/ral\nhttps://plural.gg'
USERPROXY_FOOTER_LIMIT = 400 - len(USERPROXY_FOOTER.format(username='*' * 32))


class Env(BaseEnv):
    async def _init_token(self, token: str) -> tuple[int, str]:
        from src.core.http import request, Route, get_bot_id_from_token

        user_data = await request(Route(
            'GET',
            '/applications/@me',
            token
        ))

        return (
            get_bot_id_from_token(token),
            user_data['verify_key']
        )

    async def init(self) -> None:
        with span('initializing env'):
            self._application_id, self._public_key = (
                await self._init_token(self.bot_token)
            )

            self._info_application_id, self._info_public_key = (
                await self._init_token(self.info_bot_token)
                if self.info_bot_token else
                (None, None)
            )

    @property
    def application_id(self) -> int:
        if getattr(self, '_application_id', None) is None:
            raise ValueError('env not initialized')

        return self._application_id

    @property
    def public_key(self) -> str:
        if getattr(self, '_public_key', None) is None:
            raise ValueError('env not initialized')

        return self._public_key

    @property
    def info_application_id(self) -> int | None:
        return self._info_application_id

    @property
    def info_public_key(self) -> str | None:
        return self._info_public_key

    @property
    def fp_tokens(self) -> set[str]:
        return {
            self.bot_token
        } | (
            {self.info_bot_token}
            if self.info_bot_token else
            set()
        )

    @property
    def fp_application_ids(self) -> set[int]:
        return {
            self.application_id
        } | (
            {int(self.info_application_id)}
            if self.info_application_id else
            set()
        )


env = Env.new()
