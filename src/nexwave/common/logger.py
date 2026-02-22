"""Logging configuration using Loguru"""

import sys
from loguru import logger
from typing import Optional


def setup_logging(
    level: str = "INFO",
    serialize: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """Configure Loguru logger"""

    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True,
    )

    # File handler (if specified)
    if log_file:
        logger.add(
            log_file,
            rotation="500 MB",
            retention="7 days",
            level=level,
            serialize=serialize,
            enqueue=True,  # Async logging
            backtrace=True,
            diagnose=True,
        )


# Default logger instance
__all__ = ["logger", "setup_logging"]

