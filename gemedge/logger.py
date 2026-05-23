"""Logger configuration for GemEdge using rich and rotating file handler."""

import os
import logging
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from gemedge.config import (
    OUTPUT_DIR,
    LOG_FILE_NAME,
    LOG_FORMAT,
    LOG_ENCODING,
    LOGGER_NAME
)

def setup_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Configure and return the application logger with Rich and File handlers."""
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    if log.handlers:
        return log

    # Resolve output directory absolute path relative to current working directory
    abs_output_dir = os.path.abspath(OUTPUT_DIR)
    os.makedirs(abs_output_dir, exist_ok=True)
    log_file = os.path.join(abs_output_dir, LOG_FILE_NAME)

    file_formatter = logging.Formatter(LOG_FORMAT)

    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10 MB
            backupCount=5,
            encoding=LOG_ENCODING
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        log.addHandler(file_handler)
    except OSError as e:
        print(f"Warning: Failed to set up file logger: {e}")

    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=True,
    )
    console_handler.setLevel(logging.INFO)
    log.addHandler(console_handler)

    return log

logger = setup_logger()
