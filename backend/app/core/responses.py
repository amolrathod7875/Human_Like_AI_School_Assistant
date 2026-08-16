from typing import Generic, Optional, TypeVar

from fastapi import status
from pydantic import BaseModel

from app.core.errors import RequestContext

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard envelope for all API responses."""

    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None


def success_response(data: T) -> ApiResponse[T]:
    return ApiResponse(success=True, data=data)


def error_response(
    code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    request_id: Optional[str] = None,
) -> tuple[ApiResponse, int]:
    """Return a standardized error envelope and its HTTP status code.

    Returned as a tuple so FastAPI route/exception handlers can unpack it
    directly into (body, status_code).
    """
    rid = request_id or RequestContext.get_request_id()
    return (
        ApiResponse(
            success=False,
            error=ErrorDetail(code=code, message=message, request_id=rid),
        ),
        status_code,
    )
