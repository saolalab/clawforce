"""Unified logging configuration: route stdlib logging through loguru."""

import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Intercept standard library logging and redirect to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(level: str = "INFO") -> None:
    """Configure unified logging: intercept uvicorn/stdlib logs into loguru.

    Call this before uvicorn.run() to ensure consistent log format.
    """
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(level.upper())

    for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "LiteLLM"]:
        log = logging.getLogger(name)
        log.handlers = [InterceptHandler()]
        log.propagate = False

    logger.configure(
        handlers=[
            {
                "sink": sys.stderr,
                "format": (
                    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                    "<level>{level: <8}</level> | "
                    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                    "<level>{message}</level>"
                ),
                "colorize": True,
            }
        ]
    )
