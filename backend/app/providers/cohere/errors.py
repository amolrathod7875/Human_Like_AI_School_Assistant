class LLMProviderError(Exception):
    """Raised when an LLM provider call fails.

    `retryable` signals whether the caller (or the provider's own retry loop)
    may safely retry the request.
    """

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
    ) -> None:
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(message)
