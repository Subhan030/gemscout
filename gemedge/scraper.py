"""Scraping phase entry points."""

from logger import get_logger

logger = get_logger(__name__)


async def run_phase_2(debug: bool = False) -> list[dict]:
    """Run listing-level extraction."""
    logger.info("Phase 2 is not implemented in Phase 1.")
    return []


async def run_phase_3(debug: bool = False) -> list[dict]:
    """Run bid-result extraction."""
    logger.info("Phase 3 is not implemented in Phase 1.")
    return []


async def run_phase_4(debug: bool = False) -> list[dict]:
    """Run evaluation-details extraction."""
    logger.info("Phase 4 is not implemented in Phase 1.")
    return []

