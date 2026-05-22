"""Central configuration for the GemEdge scraper."""

from pathlib import Path

BASE_URL = "https://bidplus.gem.gov.in/all-bids"
FILTER_STATUS = "Bid/RA"
FILTER_OUTCOME = "Awarded"
TARGET_ROWS = 30
MAX_RETRIES = 3
PAGE_DELAY_MIN = 1.0
PAGE_DELAY_MAX = 2.5
CHECKPOINT_PATH = "checkpoints/progress.json"
RAW_DATA_DIR = "data/raw"
OUTPUT_DIR = "output"
HEADLESS = True

PROJECT_ROOT = Path(__file__).resolve().parent
CHECKPOINTS_DIR = "checkpoints"
DATA_DIR = "data"
RAW_SUBDIR = "raw"
LOG_FILE = "run.log"

REQUIRED_DIRECTORIES = (
    CHECKPOINTS_DIR,
    f"{DATA_DIR}/{RAW_SUBDIR}",
    OUTPUT_DIR,
)

