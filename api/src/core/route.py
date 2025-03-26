from collections.abc import Callable


ROUTE_NAMES: dict[Callable, str] = {}
SUPPRESSED_PATHS: set[Callable] = set()


def name(name: str) -> Callable:
    def decorator(function: Callable) -> Callable:
        ROUTE_NAMES[function] = name
        return function

    return decorator


def suppress() -> Callable:
    def decorator(function: Callable) -> Callable:
        SUPPRESSED_PATHS.add(function)
        return function

    return decorator
