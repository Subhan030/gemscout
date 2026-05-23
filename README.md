# GemEdge - GeM Portal Procurement Data Scraper

Automated scraper for extracting structured bid and vendor data from the Government e-Marketplace (GeM) portal.

---

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Project Structure](#project-structure)
7. [Pipeline Phases](#pipeline-phases)
8. [Output Files](#output-files)
9. [Data Schema](#data-schema)
10. [Resumability](#resumability)
11. [Troubleshooting](#troubleshooting)
12. [Advanced Usage](#advanced-usage)
13. [Technical Details](#technical-details)

---

## Overview

GemEdge is a production-ready web scraper designed to extract procurement data from the GeM (Government e-Marketplace) portal. It handles complex multi-step navigation, pagination, dynamic content loading, and provides comprehensive data cleaning and validation.

**Key Features:**
- Automated pagination with auto-detection
- Checkpoint-based resumability
- Retry logic for network failures
- Duplicate prevention across runs
- Raw HTML storage for audit trail
- Fuzzy matching for vendor name normalization
- Anomaly detection and data quality flagging
- Reverse Auction (RA) detection and tracking
- Schema validation and data quality assertions

**Data Extracted:**
- 38+ bids with complete metadata
- 250+ vendor evaluation records
- Technical and financial evaluation details
- Buyer information and bid specifications
- Winner information and pricing data

---

## System Requirements

### Required Software

- **Python**: Version 3.9 or higher
- **pip**: Python package manager (usually included with Python)
- **Operating System**: macOS, Linux, or Windows
- **Internet Connection**: Required for scraping
- **Disk Space**: Minimum 100 MB for dependencies and data

### Python Dependencies

All dependencies are listed in `gemedge/requirements.txt`:

```
playwright==1.40.0
beautifulsoup4==4.12.2
lxml==4.9.3
pandas==2.1.3
rapidfuzz==3.5.2
```

---

## Installation

### Step 1: Clone or Download Project

```bash
# If using git
git clone <repository-url>
cd gemscout

# Or navigate to existing project directory
cd /path/to/gemscout
```

### Step 2: Create Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv gemedge/venv
source gemedge/venv/bin/activate
```

**On Windows:**
```bash
python -m venv gemedge\venv
gemedge\venv\Scripts\activate
```

You should see `(venv)` prefix in your terminal prompt.

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r gemedge/requirements.txt
```

This will install:
- Playwright (browser automation)
- BeautifulSoup4 (HTML parsing)
- lxml (fast XML/HTML parser)
- pandas (data processing)
- rapidfuzz (fuzzy string matching)

### Step 4: Install Playwright Browsers

```bash
playwright install chromium
```

This downloads the Chromium browser (~150 MB) used for automation.

### Step 5: Verify Installation

```bash
python gemedge/main.py --check
```

**Expected Output:**
```
Setup OK
```

If you see any errors, check the [Troubleshooting](#troubleshooting) section.

---

## Configuration

### Basic Configuration

Edit `gemedge/config.py` to customize scraper behavior:

```python
# Scraping targets
TARGET_ROWS = 30              # Number of bids to scrape
BASE_URL = "https://bidplus.gem.gov.in/all-bids"

# Retry and timing
MAX_RETRIES = 3               # Retry attempts per operation
PAGE_DELAY_MIN = 1.0          # Min delay between pages (seconds)
PAGE_DELAY_MAX = 2.5          # Max delay between pages (seconds)

# Browser settings
HEADLESS = True               # Run browser in headless mode

# File paths
CHECKPOINT_PATH = "checkpoints/progress.json"
RAW_DATA_DIR = "data/raw"
OUTPUT_DIR = "output"
```

### Filter Configuration

The scraper applies these filters by default:
- **Status**: Bid/RA
- **Outcome**: Awarded

To modify filters, edit the constants in `config.py`:
```python
FILTER_STATUS = "Bid/RA"
FILTER_OUTCOME = "Awarded"
```

### Advanced Configuration

For advanced users, additional settings are available in `config.py`:
- Selector patterns for HTML elements
- Evaluation criteria thresholds
- Logging configuration
- Output formatting options

---

## Usage

### Basic Usage

**Run Complete Pipeline:**

```bash
# Activate virtual environment
source gemedge/venv/bin/activate  # macOS/Linux
# OR
gemedge\venv\Scripts\activate     # Windows

# Run all phases
python gemedge/main.py
```

This executes all phases sequentially:
1. Phase 2: Filter and scrape listing pages
2. Phase 3: Drill down into bid details
3. Phase 4: Flatten vendor data structure
4. Phase 5: Clean and normalize data
5. Phase 6: Generate insights report
6. Phase 7: Package and validate outputs

**Expected Duration:** 5-10 minutes for initial run

### Run Specific Phase

```bash
# Run only Phase 2 (scraping)
python gemedge/main.py --phase 2

# Run only Phase 3 (drill-down)
python gemedge/main.py --phase 3

# Run only Phase 5 (cleaning)
python gemedge/main.py --phase 5

# Run only Phase 7 (packaging)
python gemedge/main.py --phase 7
```

### Debug Mode

Run with visible browser for debugging:

```bash
python gemedge/main.py --debug
```

This opens a browser window showing the scraping process in real-time.

### Command Line Options

```bash
python gemedge/main.py [OPTIONS]

Options:
  --check          Verify directories and required files exist
  --phase N        Run specific phase (2, 3, 4, 5, 6, or 7)
  --debug          Run in non-headless mode with visible browser
  -h, --help       Show help message
```

---

## Project Structure

```
gemscout/
├── gemedge/                    # Source code package
│   ├── main.py                 # Entry point and orchestrator
│   ├── scraper.py              # Web scraping logic (700+ lines)
│   ├── cleaner.py              # Data cleaning and normalization
│   ├── insights.py             # Insights generation
│   ├── packaging.py            # Output formatting and validation
│   ├── config.py               # Configuration constants (13-column schema)
│   ├── browser.py              # Browser automation setup
│   ├── checkpointing.py        # Progress tracking
│   ├── logger.py               # Logging configuration
│   ├── requirements.txt        # Python dependencies
│   └── venv/                   # Virtual environment (created during setup)
│
├── checkpoints/                # Progress checkpoints
│   └── progress.json           # Scraped data (resume point)
│
├── data/                       # Raw data storage
│   └── raw/                    # Saved HTML evaluation pages (55 files)
│       ├── GEM_2026_B_*_bid_eval.html   # Bid evaluation pages
│       ├── GEM_2026_B_*_ra_eval.html    # RA evaluation pages
│       └── GEM_2026_B_*_eval.html       # Combined evaluation pages
│
├── output/                     # Final deliverables
│   ├── bids.csv                # Flat dataset (251 rows, 13 columns)
│   ├── bids.json               # Nested dataset (38 bid objects)
│   ├── insights_report.md      # Summary insights report
│   ├── cleaned_bids.csv        # Intermediate cleaned data
│   ├── run.log                 # Detailed execution logs
│   └── writeup.md              # Technical write-up (308 words)
│
├── README.md                   # This file (comprehensive documentation)
└── .gitignore                  # Git ignore rules
```

---

## Pipeline Phases

### Phase 2: Listing-Level Extraction

**Purpose:** Scrape bid listing pages with filters applied

**Process:**
1. Navigate to GeM portal
2. Apply filters (Status=Bid/RA, Outcome=Awarded)
3. Detect total number of pages
4. Iterate through all pages
5. Extract listing-level fields from each bid card
6. Save checkpoint after each page

**Fields Extracted:**
- bid_id (Bid/RA number)
- category (Item category)
- buyer (Department name)
- quantity
- detail_url (Link to bid details)
- ra_detail_url (Link to RA details if applicable)

**Output:** `checkpoints/progress.json` with 30+ bids

### Phase 3: Drill-Down Extraction

**Purpose:** Navigate to individual bid pages and extract detailed data

**Process:**
1. Load checkpoint from Phase 2
2. For each bid:
   - Navigate to bid detail page
   - Click evaluation panel tabs
   - Extract technical evaluation table
   - Extract financial evaluation table
   - Save raw HTML for verification
   - Extract bid details (status, dates, duration)
   - Extract buyer details (name, state, organization)
   - Detect RA creation and extract RA number
3. Merge technical and financial data using fuzzy matching
4. Calculate winner and bid value
5. Save checkpoint after each bid

**Fields Extracted:**
- winner_name, winner_price, num_bidders
- bid_status, bid_start_date, bid_end_date
- bid_validity_days, contract_duration
- buyer_name, buyer_state, buyer_organisation, buyer_office
- ra_number, bid_type
- vendors array (vendor_name, vendor_rank, vendor_price)

**Output:** Updated `checkpoints/progress.json` with complete data

### Phase 4: Data Flattening

**Purpose:** Convert nested vendor arrays to flat table structure

**Process:**
1. Load checkpoint data
2. For each bid:
   - If no vendors: Create one row with bid data
   - If vendors exist: Create one row per vendor
3. Repeat bid-level fields on each vendor row
4. Enforce schema (23 columns)

**Output:** Pandas DataFrame with 250+ rows

### Phase 5: Data Cleaning

**Purpose:** Clean, normalize, and validate data

**Process:**
1. Numeric coercion (handle currency symbols, placeholders)
2. Date parsing (multiple format support)
3. Vendor name normalization (title case, suffix removal)
4. Duplicate detection (fuzzy matching >90% similarity)
5. Anomaly flagging:
   - Winner price > L2 price
   - Vendor count mismatch
   - Winner price > bid value
   - Unranked vendors
6. Repeat winner detection

**Output:** `output/cleaned_bids.csv`

### Phase 6: Insights Generation

**Purpose:** Generate summary insights report

**Analysis:**
1. Competitive bidding metrics (% with >3 bidders)
2. L1 vs L2 price gap analysis (median, mean, distribution)
3. Outlier detection (>50% price gap)
4. Repeat winner patterns
5. Market dominance check (>20% of awards)

**Output:** `output/insights_report.md` (286 words)

### Phase 7: Output Packaging

**Purpose:** Export final datasets and validate quality

**Process:**
1. Export flat CSV (vendor-level)
2. Reconstruct and export nested JSON (bid-level)
3. Run data quality assertions:
   - Minimum 30 rows
   - Schema validation (23 columns)
   - Minimum 30 unique bids
   - No null bid_ids
   - Minimum 25 bids with winners
4. Verify deliverables checklist
5. Verify raw HTML files exist

**Output:** `output/bids.csv`, `output/bids.json`

---

## Output Files

### 1. bids.csv

**Format:** Flat CSV with vendor-level rows

**Specifications:**
- Rows: 251 (varies based on TARGET_ROWS)
- Columns: 13
- Encoding: UTF-8 with BOM
- Size: ~60 KB

**Structure:**
```csv
bid_id,category,buyer,quantity,bid_value,award_date,winner_name,winner_price,num_bidders,vendor_name,vendor_rank,vendor_price,status_flag
GEM/2026/B/7484220,Cyber Security Audit - Security and Compliance Audit,Revenue and Relief Department Jammu and Kashmir,1.0,11000.0,,Cypros Technologies Private Limited Under Pma,11000.0,16,Aks Information Technology Services Private Limited Under Pma,,,unranked_vendor
```

**Use Cases:**
- Data analysis in Excel/Google Sheets
- Import into databases
- Statistical analysis
- Reporting and visualization

### 2. bids.json

**Format:** Nested JSON with bid-level objects

**Specifications:**
- Objects: 38 bids (varies based on TARGET_ROWS)
- Size: ~77 KB
- Encoding: UTF-8

**Structure:**
```json
[
  {
    "bid_id": "GEM/2026/B/7484220",
    "category": "Cyber Security Audit - Security and Compliance Audit",
    "buyer": "Revenue and Relief Department Jammu and Kashmir",
    "quantity": 1.0,
    "bid_value": 11000.0,
    "award_date": null,
    "winner_name": "Cypros Technologies Private Limited Under Pma",
    "winner_price": 11000.0,
    "num_bidders": 16,
    "status_flag": "ok",
    "vendors": [
      {
        "vendor_name": "Cypros Technologies Private Limited Under Pma",
        "vendor_rank": "L1",
        "vendor_price": 11000.0,
        "disqualified": false,
        "remarks": ""
      },
      ...
    ]
  },
  ...
]
```

**Use Cases:**
- API integration
- Web applications
- NoSQL databases
- Programmatic access

### 3. insights_report.md

**Format:** Markdown report

**Specifications:**
- Word count: 308 words
- Sections: 6 (Approach, Tools, Challenges, Failure Handling, Anomaly Detection, Vulnerabilities)
- Size: ~2.5 KB

**Contents:**
- Executive summary
- Competitive bidding analysis (78.9% with >3 bidders)
- L1 vs L2 price gap (median 3.85%, mean 9.47%)
- Outlier detection (1 bid with >50% gap)
- Repeat winner patterns (4 vendors)
- Market dominance check (no vendor >20%)

### 4. run.log

**Format:** Plain text log file

**Specifications:**
- Size: ~47 KB
- Encoding: UTF-8
- Format: `YYYY-MM-DD HH:MM:SS - LEVEL - MESSAGE`

**Contents:**
- Timestamp for each operation
- Phase execution logs
- Error messages and stack traces
- Performance metrics
- Data quality warnings

**Use Cases:**
- Debugging
- Performance analysis
- Audit trail
- Error diagnosis

### 5. cleaned_bids.csv

**Format:** Intermediate cleaned CSV

**Purpose:** Cleaned data before final packaging (for debugging)

### 6. Raw HTML Files

**Location:** `data/raw/`

**Files:** 55 HTML files
- `GEM_2026_B_XXXXXXX_bid_eval.html` - Bid evaluation pages
- `GEM_2026_B_XXXXXXX_ra_eval.html` - RA evaluation pages
- `GEM_2026_B_XXXXXXX_eval.html` - Combined evaluation pages

**Purpose:**
- Verification of extraction accuracy
- Re-extraction without re-scraping
- Debugging parsing issues
- Audit trail

---

## Data Schema

### Column Definitions

**Total Columns:** 13

| # | Column Name | Type | Description | Example |
|---|-------------|------|-------------|---------|
| 1 | bid_id | string | Bid number | GEM/2026/B/7484220 |
| 2 | category | string | Item category | Cyber Security Audit |
| 3 | buyer | string | Department name | Revenue and Relief Department Jammu and Kashmir |
| 4 | quantity | float | Quantity | 1.0 |
| 5 | bid_value | float | Total bid value (winner_price × quantity) | 11000.0 |
| 6 | award_date | datetime | Award date (currently not available from portal) | NULL |
| 7 | winner_name | string | L1 winner name | Cypros Technologies Private Limited Under Pma |
| 8 | winner_price | float | L1 winner price | 11000.0 |
| 9 | num_bidders | int | Number of participating vendors | 16 |
| 10 | vendor_name | string | Vendor name | Cypros Technologies Private Limited Under Pma |
| 11 | vendor_rank | string | Vendor rank (L1, L2, L3, ...) | L1 |
| 12 | vendor_price | float | Vendor quoted price | 11000.0 |
| 13 | status_flag | string | Data quality flag | ok |

### Important Notes

**award_date Field:**
- Currently empty across all records
- GeM portal does not publicly expose actual contract award dates
- Only submission deadlines are available on listing pages
- This field is reserved for future use if award dates become available

**Null Values in vendor_rank:**
- Approximately 50% of vendor rows have null ranks
- This is expected and correct
- These vendors participated in technical evaluation but did not submit financial bids
- Flagged as `unranked_vendor` in status_flag

**Simplified Schema:**
- Reduced from 24 columns to 13 core fields
- Removed: ra_number, bid_type, buyer details (name, state, organisation, office), bid dates (start_date, end_date, validity_days), bid_status, contract_duration, tech_status
- Focus on essential bid and vendor information for analysis

### Status Flags

| Flag | Description | Count (typical) |
|------|-------------|-----------------|
| ok | Clean record with no issues | 79 |
| unranked_vendor | Vendor participated but didn't submit financial bid | 85 |
| possible_dup | Potential duplicate vendor name (>90% similarity) | 24 |
| anomaly_winner_not_l1 | Winner price > L2 price | Rare |
| anomaly_count_mismatch | Vendor count doesn't match num_bidders | Rare |
| anomaly_price_exceeds_bid | Winner price > bid value | Rare |
| repeat_winner | Vendor won multiple bids (appended to other flags) | 63 |
| no_result | No evaluation data found | Rare |
| nav_error | Navigation error during scraping | Rare |

---

## Resumability

### How It Works

The scraper implements a robust checkpoint system that allows it to resume from any interruption point:

**1. Atomic Checkpointing**
- Progress saved to `checkpoints/progress.json` after every page (Phase 2) and every bid (Phase 3)
- Uses atomic write (temp file + rename) to prevent corruption
- If interrupted mid-write, either old or new checkpoint exists (never corrupted)

**2. Duplicate Prevention**
- Builds set of scraped `bid_id`s on startup
- Skips bids already in checkpoint
- Works across multiple runs and interruptions

**3. Raw HTML Storage**
- All evaluation pages saved to `data/raw/`
- Can re-extract data without re-scraping
- Complete audit trail

### Resume Scenarios

**Scenario 1: Interrupted During Scraping (Phase 2)**
```bash
# Run 1: Scrapes pages 1-3 (30 bids) → Network error
python gemedge/main.py

# Checkpoint: 30 bids saved

# Run 2: Loads 30 bids → Skips pages 1-3 → Continues from page 4
python gemedge/main.py
```

**Scenario 2: Interrupted During Drill-Down (Phase 3)**
```bash
# Run 1: Processes 20 bids → Crash
python gemedge/main.py

# Checkpoint: 20 bids with complete data, 10 bids with partial data

# Run 2: Loads checkpoint → Skips 20 complete bids → Processes remaining 10
python gemedge/main.py
```

**Scenario 3: Re-run After Completion**
```bash
# Run 1: Completes all 38 bids
python gemedge/main.py

# Run 2: Detects 38 bids already scraped → Skips scraping → Runs cleaning/packaging only
python gemedge/main.py
```

### Manual Checkpoint Management

**View Checkpoint:**
```bash
cat checkpoints/progress.json | python -m json.tool | head -50
```

**Check Checkpoint Size:**
```bash
python -c "import json; data = json.load(open('checkpoints/progress.json')); print(f'Bids: {len(data)}')"
```

**Reset Checkpoint (Start Fresh):**
```bash
rm checkpoints/progress.json
python gemedge/main.py
```

**Backup Checkpoint:**
```bash
cp checkpoints/progress.json checkpoints/progress_backup_$(date +%Y%m%d_%H%M%S).json
```

---

## Troubleshooting

### Installation Issues

**Problem:** `python3: command not found`

**Solution:**
```bash
# macOS: Install Python via Homebrew
brew install python3

# Linux: Install via package manager
sudo apt-get install python3 python3-pip  # Ubuntu/Debian
sudo yum install python3 python3-pip      # CentOS/RHEL

# Windows: Download from python.org
```

**Problem:** `pip: command not found`

**Solution:**
```bash
python3 -m ensurepip --upgrade
```

**Problem:** `playwright install` fails

**Solution:**
```bash
# Install system dependencies (Linux only)
playwright install-deps

# Then retry
playwright install chromium
```

### Runtime Issues

**Problem:** `ModuleNotFoundError: No module named 'gemedge'`

**Solution:**
```bash
# Ensure virtual environment is activated
source gemedge/venv/bin/activate

# Verify activation (should see (venv) prefix)
which python

# Reinstall dependencies
pip install -r gemedge/requirements.txt
```

**Problem:** `No bids scraped` or `Found 0 cards on page 1`

**Possible Causes:**
1. Portal is down or changed structure
2. Network connectivity issues
3. Filters not applying correctly

**Solution:**
```bash
# Run in debug mode to see browser
python gemedge/main.py --debug

# Check portal manually
open https://bidplus.gem.gov.in/all-bids

# Check logs
tail -100 output/run.log
```

**Problem:** `Navigation timeout` or `Page load timeout`

**Solution:**
```bash
# Increase retry count in config.py
MAX_RETRIES = 5

# Increase delays
PAGE_DELAY_MIN = 2.0
PAGE_DELAY_MAX = 5.0

# Check internet connection
ping bidplus.gem.gov.in
```

**Problem:** `Checkpoint corrupted` or `JSON decode error`

**Solution:**
```bash
# Backup corrupted checkpoint
mv checkpoints/progress.json checkpoints/progress_corrupted.json

# Start fresh
python gemedge/main.py
```

### Data Quality Issues

**Problem:** Many `unranked_vendor` flags

**Explanation:** This is expected. Vendors who participate in technical evaluation but don't submit financial bids have null ranks.

**Problem:** `possible_dup` flags

**Explanation:** Vendor names with >90% similarity are flagged. Review manually:
```bash
python -c "
import pandas as pd
df = pd.read_csv('output/bids.csv')
dups = df[df['status_flag'].str.contains('possible_dup', na=False)]
print(dups[['vendor_name', 'status_flag']].drop_duplicates())
"
```

**Problem:** Missing buyer_state or contract_duration

**Explanation:** These fields are optional on the portal. Null values are expected when not provided.

### Performance Issues

**Problem:** Scraping is very slow

**Solution:**
```bash
# Reduce delays (but may trigger rate limiting)
PAGE_DELAY_MIN = 0.5
PAGE_DELAY_MAX = 1.0

# Reduce target rows for testing
TARGET_ROWS = 10
```

**Problem:** High memory usage

**Explanation:** Pandas and BeautifulSoup can use significant memory. This is normal for data processing.

### Logging and Debugging

**View Recent Logs:**
```bash
tail -50 output/run.log
```

**Search Logs for Errors:**
```bash
grep ERROR output/run.log
grep WARNING output/run.log
```

**Enable Debug Logging:**

Edit `gemedge/logger.py`:
```python
logger.setLevel(logging.DEBUG)  # Change from INFO to DEBUG
```

---

## Advanced Usage

### Custom Filters

To scrape different bid types, edit `gemedge/config.py`:

```python
# Scrape only active bids
FILTER_STATUS = "Bid"
FILTER_OUTCOME = "Active"

# Scrape all bids (no outcome filter)
# Comment out or modify filter application in scraper.py
```

### Increase Scraping Target

```python
# In config.py
TARGET_ROWS = 100  # Scrape 100 bids instead of 30
```

**Note:** Larger targets increase execution time proportionally.

### Parallel Processing

The current implementation is sequential. For parallel processing:

1. Run multiple instances with different filters
2. Merge checkpoints manually
3. Or modify `scraper.py` to use asyncio.gather() for concurrent bid processing

### Custom Data Processing

Add custom processing in Phase 5:

```python
# In gemedge/cleaner.py, add custom logic to clean_data()

def clean_data(raw_data: list[dict]) -> pd.DataFrame:
    # ... existing code ...
    
    # Add custom processing
    df['custom_field'] = df['category'].str.upper()
    df['price_per_unit'] = df['bid_value'] / df['quantity']
    
    return df
```

### Export to Database

After Phase 7, export to database:

```python
import pandas as pd
from sqlalchemy import create_engine

# Read CSV
df = pd.read_csv('output/bids.csv')

# Export to PostgreSQL
engine = create_engine('postgresql://user:pass@localhost/dbname')
df.to_sql('bids', engine, if_exists='replace', index=False)

# Export to SQLite
engine = create_engine('sqlite:///bids.db')
df.to_sql('bids', engine, if_exists='replace', index=False)
```

### Scheduled Execution

Run scraper on schedule using cron (Linux/macOS):

```bash
# Edit crontab
crontab -e

# Add line to run daily at 2 AM
0 2 * * * cd /path/to/gemscout && source gemedge/venv/bin/activate && python gemedge/main.py >> output/cron.log 2>&1
```

Or use Windows Task Scheduler on Windows.

---

## Technical Details

### Technologies Used

**Web Scraping:**
- Playwright 1.40.0 - Browser automation
- BeautifulSoup4 4.12.2 - HTML parsing
- lxml 4.9.3 - Fast XML/HTML parser

**Data Processing:**
- pandas 2.1.3 - Data manipulation and analysis
- rapidfuzz 3.5.2 - Fuzzy string matching

**Architecture:**
- Async/await pattern for browser automation
- Checkpoint-based state management
- Modular phase-based pipeline
- Atomic file operations for data integrity

### Browser Automation

**Anti-Detection Measures:**
- Bypasses DevTools detection
- Hides webdriver property
- Uses realistic user agent
- Random delays between requests

**Dynamic Content Handling:**
- Waits for network idle
- Waits for specific selectors
- Executes JavaScript for hidden elements
- Verifies page transitions

### Data Quality

**Validation Checks:**
- Schema enforcement (13 columns)
- Type validation (numeric, date, string)
- Null value handling
- Duplicate detection
- Anomaly flagging
- Cross-field validation

**Cleaning Operations:**
- Vendor name normalization
- Currency symbol removal
- Date format standardization
- Whitespace normalization
- Suffix stripping

### Performance

**Typical Execution Times:**
- Phase 2 (Scraping): 3-5 minutes for 30 bids
- Phase 3 (Drill-down): 2-3 minutes for 30 bids
- Phase 4-7 (Processing): <1 minute
- **Total**: 5-10 minutes for complete pipeline

**Resource Usage:**
- Memory: ~200-300 MB
- Disk: ~100 MB (including dependencies)
- Network: ~50 MB download (HTML pages)

### Limitations

**Portal Limitations:**
- True award date not exposed (only submission deadline)
- Some buyer fields may be redacted (shown as ***)
- Contract duration not always provided
- RA numbers not directly linked from bid pages

**Scraper Limitations:**
- Sequential processing (not parallel)
- Requires stable internet connection
- Portal structure changes may break selectors
- Rate limiting not implemented (relies on delays)

**Data Limitations:**
- ~50% of vendors have null ranks (expected - didn't submit financial bids)
- Some fields optional (buyer_state, contract_duration)
- Vendor name variations require fuzzy matching
- Historical data not available (only current listings)

---

## Support and Maintenance

### Getting Help

1. **Check Logs:** `output/run.log` contains detailed error messages
2. **Debug Mode:** Run with `--debug` to see browser in action
3. **Verify Setup:** Run `python gemedge/main.py --check`

### Reporting Issues

When reporting issues, include:
1. Error message from `output/run.log`
2. Command used
3. Python version (`python --version`)
4. Operating system
5. Steps to reproduce

### Contributing

To contribute improvements:
1. Test changes thoroughly
2. Update documentation
3. Follow existing code style
4. Add comments for complex logic

### Maintenance

**Regular Maintenance:**
- Update dependencies: `pip install --upgrade -r gemedge/requirements.txt`
- Update Playwright: `playwright install chromium`
- Clear old checkpoints: `rm checkpoints/progress_*.json`
- Archive old outputs: `mv output output_$(date +%Y%m%d)`

**Portal Changes:**
If portal structure changes:
1. Update selectors in `config.py`
2. Update parsing logic in `scraper.py`
3. Test with `--debug` mode
4. Update documentation

---

## License

This project is for educational and research purposes. Ensure compliance with the GeM portal's terms of service when using this scraper.

---

## Additional Resources

- **output/writeup.md** - Technical write-up and challenges faced (308 words)
- **output/insights_report.md** - Procurement insights and analysis
- **output/run.log** - Detailed execution logs for debugging

---

## Acknowledgments

This scraper was built to extract procurement data from the Government e-Marketplace (GeM) portal for analysis and research purposes. It demonstrates best practices in web scraping including resumability, data quality validation, and comprehensive error handling.
