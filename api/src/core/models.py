from __future__ import annotations

from plural.env import Env as BaseEnv
from plural.otel import span


LEGACY_FOOTERS = {
    'userproxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural',
    'a plural proxy for @{username} powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
}
USERPROXY_FOOTER = '\n\na plural proxy for @{username} powered by /plu/ral\nhttps://plural.gg'
USERPROXY_FOOTER_LIMIT = 400 - len(USERPROXY_FOOTER.format(username='*' * 32))


class Env(BaseEnv):
    async def init(self) -> None:
        from src.core.http import request, Route, get_bot_id_from_token

        self._application_id = get_bot_id_from_token(self.bot_token)

        with span('initializing env'):
            user_data = await request(Route(
                'GET',
                '/applications/@me',
                self.bot_token
            ))

        self._public_key = user_data['verify_key']

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


env = Env.new()
