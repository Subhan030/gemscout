"""CLI orchestration for the GemEdge scraper."""

import argparse
import asyncio
import logging
import time
from pathlib import Path

from config import PROJECT_ROOT, REQUIRED_DIRECTORIES
from logger import get_logger, setup_logger

logger = get_logger(__name__)


def verify_setup() -> None:
    """Validate the Phase 1 project structure."""
    missing_directories = [
        directory
        for directory in REQUIRED_DIRECTORIES
        if not (PROJECT_ROOT / directory).is_dir()
    ]
    if missing_directories:
        joined = ", ".join(missing_directories)
        raise RuntimeError(f"Missing required directories: {joined}")
    print("Setup OK")


async def run_all_phases(debug: bool = False) -> None:
    """Run the implemented scraper phases."""
    logger.info("Phase execution is not implemented beyond setup yet.")
    if debug:
        logger.debug("Debug mode enabled.")


async def run_selected_phase(phase: int, debug: bool = False) -> None:
    """Run a single scraper phase by number."""
    logger.info("Requested phase %s", phase)
    if phase == 1:
        verify_setup()
        return
    logger.info("Only Phase 1 setup is implemented.")
    if debug:
        logger.debug("Debug mode enabled.")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="GemEdge procurement scraper")
    parser.add_argument("--phase", type=int, choices=range(1, 8), help="Run one phase")
    parser.add_argument("--check", action="store_true", help="Verify setup only")
    parser.add_argument("--debug", action="store_true", help="Run browser visibly with slow motion")
    return parser.parse_args()


def main() -> None:
    """Run the CLI entry point."""
    args = parse_args()
    setup_logger(logging.DEBUG if args.debug else logging.INFO)
    started_at = time.perf_counter()

    if args.check:
        verify_setup()
    elif args.phase:
        asyncio.run(run_selected_phase(args.phase, args.debug))
    else:
        asyncio.run(run_all_phases(args.debug))

    elapsed = time.perf_counter() - started_at
    logger.info("Total wall-clock time: %.2fs", elapsed)


if __name__ == "__main__":
    main()

