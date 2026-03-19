"""
Logging configuration for the Binance Futures trading bot.
Sets up both file and console handlers with structured formatting.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_level: str = "INFO",
    log_to_console: bool = True,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> logging.Logger:
    """
    Configure root logger with rotating file handler and optional console handler.

    Args:
        log_level:       Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_to_console:  Whether to also emit logs to stdout.
        max_bytes:       Maximum size of each log file before rotation.
        backup_count:    Number of rotated log files to retain.

    Returns:
        The configured root logger.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid adding duplicate handlers if setup_logging is called more than once
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Rotating file handler
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler (optional)
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings+ to console
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger."""
    return logging.getLogger(name)
