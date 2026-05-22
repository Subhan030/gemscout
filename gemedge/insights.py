"""Insight generation entry points."""

import pandas as pd

from logger import get_logger

logger = get_logger(__name__)


def write_insights_report(df: pd.DataFrame) -> None:
    """Write the insights report in later phases."""
    logger.info("Phase 6 is not implemented in Phase 1.")

