from __future__ import annotations

from datetime import timedelta

from .redis import BaseRedisModel


# ? these are only created when a message is proxied
# ? in a server with logclean enabled
class ProxyLog(BaseRedisModel):
    class Meta:
        model_key_prefix = 'proxy_log'
        expire = timedelta(seconds=60)

    author: str | None = None
    message: str | None = None
    author_name: str | None = None
    channel: str | None = None
    content: str | None = None
