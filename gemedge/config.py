"""Configuration constants for GemEdge scraper."""

BASE_URL = "https://bidplus.gem.gov.in/all-bids"
FILTER_STATUS = "Bid/RA"
FILTER_OUTCOME = "Awarded"
TARGET_ROWS = 30
MAX_RETRIES = 3
PAGE_DELAY_MIN = 1.0   # seconds
PAGE_DELAY_MAX = 2.5   # seconds
CHECKPOINT_PATH = "checkpoints/progress.json"
RAW_DATA_DIR = "data/raw"
OUTPUT_DIR = "output"
INSIGHTS_REPORT_PATH = "output/insights_report.md"
BIDS_CSV_PATH = "output/bids.csv"
BIDS_JSON_PATH = "output/bids.json"
WRITEUP_PATH = "output/writeup.md"
RUN_LOG_PATH = "output/run.log"
HEADLESS = True

# Logging configuration constants
LOG_FILE_NAME = "run.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_ENCODING = "utf-8"
LOGGER_NAME = "gemedge"

# Browser configuration constants
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BLOCKED_RESOURCE_TYPES = ("image", "font")
ROUTE_GLOB = "**/*"

# General encoding and file constants
ENCODING = "utf-8"
TMP_EXT = ".tmp"
READ_MODE = "r"
WRITE_MODE = "w"

# Output messages
SETUP_OK_MSG = "Setup OK"

# Playwright & BeautifulSoup Selectors
FILTER_STATUS_CHECKBOX = "#bidrastatus"
FILTER_OUTCOME_CHECKBOX = "#bid_awarded"
SEARCH_BUTTON = "#searchBidRA"
BID_CARD_SELECTOR = "#bidCard .card"
PAGINATION_LINKS = "#light-pagination a.page-link"
PAGINATION_NEXT = "#light-pagination a.page-link.next"
TOTAL_RECORD_SELECTOR = ".totalRecord"
BID_NO_HOVER_SELECTOR = "a.bid_no_hover"
START_DATE_SELECTOR = ".start_date"
END_DATE_SELECTOR = ".end_date"

# Global JS Function names for filtering
JS_STATUS_TYPE_FILTER = "bidStatusTypeFilter('bidrastatus')"
JS_STATUS_FILTER = "bidStatusFilter('bid_awarded')"

# URL prefixes/substrings
BID_DOCUMENT_PREFIX = "showbidDocument"
RA_DOCUMENT_PREFIX = "showradocumentPdf"
RESULT_VIEW_PREFIX = "getBidResultView"
GEM_BASE_DOMAIN = "https://bidplus.gem.gov.in"

# Detail page selectors for evaluation panels
TECH_EVAL_PANEL = "#collapseTwo"
FIN_EVAL_PANEL = "#collapseThree"
TECH_EVAL_LINK = 'a[href="#collapseTwo"]'
FIN_EVAL_LINK = 'a[href="#collapseThree"]'

# Insights metrics thresholds and truncation limits
COMPETITIVE_BIDDERS_THRESHOLD = 3
OUTLIER_PRICE_GAP_THRESHOLD = 50.0
REPEAT_WINNER_WINS_THRESHOLD = 1
DOMINANCE_PERCENT_THRESHOLD = 20.0

MAX_VENDOR_DISPLAY_LEN = 35
MAX_CATEGORY_DISPLAY_LEN = 30
MAX_CATEGORIES_PER_VENDOR = 2

# Final output schema — columns in this exact order
REQUIRED_COLUMNS = [
    "bid_id",
    "category",
    "buyer",
    "quantity",
    "bid_value",
    "award_date",
    "winner_name",
    "winner_price",
    "num_bidders",
    "vendor_name",
    "vendor_rank",
    "vendor_price",
    "status_flag",
]


