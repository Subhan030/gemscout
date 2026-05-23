"""Atomic checkpoint save and load utilities for GemEdge."""

import json
import os
from typing import List, Dict
from gemedge.config import ENCODING, TMP_EXT, READ_MODE, WRITE_MODE
from gemedge.logger import logger

def save_checkpoint(data: List[Dict], path: str) -> None:
    """Atomically save the current scraper progress list to a JSON file."""
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    tmp_path = f"{path}{TMP_EXT}"
    try:
        with open(tmp_path, WRITE_MODE, encoding=ENCODING) as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp_path, path)
        logger.debug(f"Atomically saved progress checkpoint to '{path}'")
    except Exception as e:
        logger.error(f"Failed to write checkpoint to '{path}': {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as cleanup_err:
                logger.error(f"Failed to clean up temporary checkpoint file: {cleanup_err}")
        raise e

def load_checkpoint(path: str) -> List[Dict]:
    """Load existing progress from a JSON file, returning an empty list if it does not exist."""
    if not os.path.exists(path):
        logger.debug(f"Checkpoint file '{path}' does not exist. Starting a new session.")
        return []

    try:
        with open(path, READ_MODE, encoding=ENCODING) as f:
            data = json.load(f)
            logger.info(f"Successfully loaded checkpoint from '{path}' ({len(data)} items)")
            return data
    except Exception as e:
        logger.error(f"Failed to load checkpoint file '{path}': {e}. Returning empty list.")
        return []
