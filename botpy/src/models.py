from plural.env import Env as BaseEnv


class Env(BaseEnv):
    @property
    def application_id(self) -> int:
        if getattr(self, '_application_id', None) is None:
            from src.http import get_bot_id_from_token
            self._application_id = get_bot_id_from_token(self.bot_token)

        return self._application_id


env = Env.new()
