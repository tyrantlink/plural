from typing import Callable, Awaitable
from .types import ListenerType
from asyncio import gather


__listeners: dict[ListenerType, list[Callable[..., Awaitable[None]]]] = {}


def listen(event_name: ListenerType):
    def decorator(func: Callable[..., Awaitable[None]]):
        if event_name not in __listeners:
            __listeners[event_name] = []
        __listeners[event_name].append(func)
        return func
    return decorator


async def emit(event_name: ListenerType, *args, **kwargs):
    if event_name in __listeners:
        await gather(*[
            listener(*args, **kwargs)
            for listener in __listeners[event_name]
        ])
