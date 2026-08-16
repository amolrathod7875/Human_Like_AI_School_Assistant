from typing import Optional

from app.core.errors import AppError


class VapiError(Exception):
    """Base error for the Vapi adapter/provider boundary.

    Kept separate from `AppError` so the provider stays independent of the web
    layer (mirrors how `LLMProviderError` lives in the Cohere provider). The API
    route translates these into `AppError` at the boundary.
    """

    code: str = "VAPI_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class VapiWebhookError(VapiError):
    """Raised when a webhook cannot be authenticated or parsed."""

    code = "WEBHOOK_ERROR"
    status_code = 400


def to_app_error(exc: VapiError) -> AppError:
    """Translate a provider error into the standard web error envelope type."""
    return AppError(exc.message, exc.code, status_code=exc.status_code)
