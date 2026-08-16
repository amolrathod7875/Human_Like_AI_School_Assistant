import logging
import sys
from typing import Optional

from app.core.config import settings
from app.core.errors import RequestContext


class RequestIdFilter(logging.Filter):
    """Injects the current request id (if any) into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = RequestContext.get_request_id() or "-"
        return True


def configure_logging(level: Optional[str] = None) -> None:
    """Configure root logging with a structured, request-aware formatter."""
    log_level = (level or settings.LOG_LEVEL or "INFO").upper()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt=(
                "%(asctime)s %(levelname)s %(name)s "
                "[req_id=%(request_id)s] %(message)s"
            )
        )
    )
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)

    # Quiet down noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that emits request-aware structured records."""
    return logging.getLogger(name)
