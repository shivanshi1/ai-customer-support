"""Application-specific exceptions and API error responses."""

from collections.abc import Callable

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for deliberate application errors."""

    status_code = 500
    code = "internal_error"
    message = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"


class ServiceUnavailableError(AppError):
    """Raised when a required upstream provider is unavailable."""

    status_code = 503
    code = "service_unavailable"


class UpstreamResponseError(AppError):
    """Raised when an upstream model returns an invalid response."""

    status_code = 502
    code = "upstream_response_invalid"
    message = "The AI provider returned an invalid response."


def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """Return the consistent public error format for known failures."""

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": exc.message}},
    )


ExceptionHandler = Callable[[Request, AppError], JSONResponse]
