from contextvars import ContextVar
from typing import Any, Optional

from fastapi import status

# Per-request context. ContextVars are the correct primitive: each request runs
# in its own context so the request id is isolated across concurrent requests.
_request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class RequestContext:
    """Holds per-request contextual data (e.g. request id) used in logs/errors."""

    @staticmethod
    def set_request_id(request_id: str) -> None:
        _request_id_var.set(request_id)

    @staticmethod
    def get_request_id() -> Optional[str]:
        return _request_id_var.get()

    @staticmethod
    def reset() -> None:
        _request_id_var.set(None)


class AppError(Exception):
    """Base application error with a stable error code and HTTP status.

    Other modules should subclass this for domain-specific errors so that the
    global exception handler can serialize a standardized error response.
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Any] = None,
    ) -> None:
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        super().__init__(message)
