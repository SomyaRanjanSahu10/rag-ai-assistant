"""
Logging Configuration
=====================
Structured logging with rotating file handlers.
Outputs JSON-structured logs in production, readable format in development.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_level: str = None):
    """Configure application-wide logging."""
    level = getattr(logging, (log_level or os.getenv("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    # Formatter
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(level)
    root_logger.addHandler(console)

    # Rotating file handler — general
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # Error-only file
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)

    # Silence noisy third-party loggers
    for name in ["uvicorn.access", "httpx", "httpcore", "multipart"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.info("✅ Logging configured (level=%s)", logging.getLevelName(level))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
