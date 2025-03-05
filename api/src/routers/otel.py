from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import Request, HTTPException

from plural.otel import span


def trace[T](name: str) -> Callable[[T], T]:
    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(
            request: Request,
            *args: Any,  # noqa: ANN401
            **kwargs: Any  # noqa: ANN401
        ) -> Any:  # noqa: ANN401
            with span(
                f'{request.method} {name}',
                attributes={
                    'http.method': request.method,
                    'http.route': request.url.path}
            ) as current_span:
                try:
                    response = await func(request, *args, **kwargs)
                except HTTPException as e:
                    current_span.set_attribute(
                        'http.status_code',
                        e.status_code)
                    raise

                current_span.set_attribute(
                    'http.status_code',
                    response.status_code
                )

                return response

        return wrapper
    return decorator
