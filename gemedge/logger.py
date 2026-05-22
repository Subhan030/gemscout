"""Logging setup for console and file output."""

import logging
from pathlib import Path

from config import LOG_FILE, OUTPUT_DIR, PROJECT_ROOT

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """Configure root logging with rich console and file handlers."""
    output_dir = PROJECT_ROOT / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / LOG_FILE

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    try:
        from rich.logging import RichHandler

        console_handler = RichHandler(
            rich_tracebacks=True,
            show_time=True,
            show_level=True,
            show_path=False,
        )
    except ModuleNotFoundError:
        console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(name)s %(message)s"))

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
