from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file.

    Never hardcode secrets. Provide them via environment variables or .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Service identity
    PROJECT_NAME: str = "xyz-ai-backend"
    SERVICE_NAME: str = "xyz-ai-backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"

    # CORS (comma-separated list or JSON array via env)
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"

    # Request identity
    REQUEST_ID_HEADER: str = "X-Request-ID"

    # Firebase Authentication (service-account credentials, never hardcoded)
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CLIENT_EMAIL: Optional[str] = None
    FIREBASE_PRIVATE_KEY: Optional[str] = None

    # Cohere LLM provider (API key is a secret; provide via env / secret manager)
    COHERE_API_KEY: Optional[str] = None
    COHERE_MODEL: str = "command-r-plus"
    COHERE_TIMEOUT: int = 30
    COHERE_MAX_RETRIES: int = 1

    # AI orchestrator (no secrets; tuning only)
    AI_CONTEXT_MESSAGE_LIMIT: int = 10  # conversation turns given to the model
    AI_MAX_TOOL_CALLS: int = 3  # tool calls allowed in a single turn

    # Vapi voice provider (Section 14).
    # The webhook signing secret is a secret; provide via env / secret manager.
    VAPI_WEBHOOK_SECRET: Optional[str] = None
    # Optional REST API key if outbound Vapi calls are needed (not required for
    # the inbound webhook flow). Provide via env / secret manager.
    VAPI_API_KEY: Optional[str] = None
    # Name of the Vapi assistant tool that forwards the user's spoken transcript
    # to this backend. Vapi performs STT; this backend stays the brain (TTS is
    # handled by Vapi from the returned text).
    VAPI_VOICE_TOOL_NAME: str = "process_voice"
    # When True, inbound webhooks must carry a valid X-Vapi-Signature. Set False
    # only for local development without a configured secret.
    VAPI_WEBHOOK_VERIFY: bool = True


def get_settings() -> Settings:
    """Return the cached application settings."""
    return Settings()


# Module-level singleton used across the application.
settings: Settings = get_settings()
