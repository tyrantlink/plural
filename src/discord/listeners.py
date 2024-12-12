from src.errors import on_interaction_error, on_event_error
from collections.abc import Callable, Awaitable
from .types import ListenerType
from asyncio import gather


__listeners: dict[ListenerType, list[Callable[..., Awaitable[None]]]] = {}


def listen(event_name: ListenerType) -> Callable[..., Callable[..., Awaitable[None]]]:
    def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
        if event_name not in __listeners:
            __listeners[event_name] = []
        __listeners[event_name].append(func)
        return func
    return decorator


async def emit(event_name: ListenerType, *args, **kwargs) -> None: # noqa: ANN002, ANN003
    if event_name in __listeners:
        for exception in await gather(*[
            listener(*args, **kwargs)
            for listener in __listeners[event_name]],
            return_exceptions=True
        ):
            if exception is None:
                continue

            match event_name:
                case ListenerType.INTERACTION:
                    interaction = args[0]
                    await on_interaction_error(interaction, exception)
                case _:
                    await on_event_error(event_name.name, exception)
