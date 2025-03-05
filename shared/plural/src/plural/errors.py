from __future__ import annotations

from typing import Any


class BasePluralException(Exception):
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)


class PluralException(BasePluralException):
    ...


class PluralExceptionCritical(PluralException):
    ...


class HTTPException(BasePluralException):
    status_code: int = 0

    def __init__(self, detail: Any | None = None) -> None:  # noqa: ANN401
        self.detail = detail
        super().__init__(detail)


class BadRequest(HTTPException):
    status_code: int = 400

    def __init__(self, detail: dict | None = None) -> None:
        super().__init__(detail)


class Unauthorized(HTTPException):
    status_code: int = 401


class Forbidden(HTTPException):
    status_code: int = 403


class NotFound(HTTPException):
    status_code: int = 404


class ServerError(HTTPException):
    status_code: int = 500


class ImageLimitExceeded(HTTPException):
    ...


class ConversionError(BasePluralException):
    ...


class InteractionError(BasePluralException):
    ...


class DuplicateEventError(BasePluralException):
    ...
