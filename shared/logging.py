"""Shared structlog configuration for all services.

Usage in any module:
    from shared.logging import get_logger
    logger = get_logger()
    logger.info("something happened", device_id="solar-1")
"""
import logging
import sys

import structlog


def setup_logging(service_name: str, level: str = "INFO") -> None:
    """Configure structlog with JSON rendering for all services.

    Call once at service startup (before any loggers are created).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so third-party libraries (uvicorn, sqlalchemy, etc.)
    # produce structured output through the same handler.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Add service name to all log entries via structlog context
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(*args, **kwargs) -> structlog.stdlib.BoundLogger:
    """Return a structlog BoundLogger (drop-in replacement for logging.getLogger)."""
    return structlog.get_logger(*args, **kwargs)
