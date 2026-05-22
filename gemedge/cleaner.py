"""Data cleaning phase entry points."""

import pandas as pd

from logger import get_logger

logger = get_logger(__name__)


def clean_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Return a dataframe for later cleaning phases."""
    logger.info("Phase 5 is not implemented in Phase 1.")
    return pd.DataFrame(rows)

