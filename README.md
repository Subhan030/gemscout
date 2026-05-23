# GemEdge - GeM Portal Procurement Data Scraper

Automated scraper for extracting structured bid and vendor data from India's Government e-Marketplace (GeM) portal.

## Features

- Automated pagination with checkpoint-based resumability
- Retry logic and error handling
- Fuzzy vendor name matching
- Anomaly detection and data quality flagging
- Raw HTML storage for audit trail

**Output:** 38 bids, 251 vendor records with 13-column schema

---

## Quick Start

```bash
# Setup
python3 -m venv gemedge/venv
source gemedge/venv/bin/activate
pip install -r gemedge/requirements.txt
playwright install chromium

# Run
python gemedge/main.py

# Debug mode
python gemedge/main.py --debug
```

---

## Project Structure

```
gemscout/
├── gemedge/                    # Source code
│   ├── main.py                 # Entry point
│   ├── scraper.py              # Web scraping logic
│   ├── cleaner.py              # Data cleaning
│   ├── insights.py             # Insights generation
│   ├── packaging.py            # Output formatting
│   ├── config.py               # Configuration
│   ├── browser.py              # Browser automation
│   ├── checkpointing.py        # Progress tracking
│   ├── logger.py               # Logging
│   ├── requirements.txt        # Dependencies
│   └── venv/                   # Virtual environment
│
├── checkpoints/                # Progress checkpoints
│   └── progress.json           # Scraped data (resume point)
│
├── data/raw/                   # Raw HTML files (55 files)
│
├── output/                     # Final deliverables
│   ├── bids.csv                # Flat dataset (251 rows, 13 columns)
│   ├── bids.json               # Nested dataset (38 bids)
│   ├── insights_report.md      # Summary insights
│   ├── cleaned_bids.csv        # Intermediate cleaned data
│   ├── run.log                 # Execution logs
│   └── writeup.md              # Technical write-up
│
├── README.md                   # This file
└── .gitignore                  # Git ignore rules
```

---

## Data Schema

**13 Columns:**

| Column | Type | Description |
|--------|------|-------------|
| bid_id | string | Bid number (e.g., GEM/2026/B/7484220) |
| category | string | Item category |
| buyer | string | Department name |
| quantity | float | Quantity |
| bid_value | float | Total value (winner_price × quantity) |
| award_date | datetime | Award date (currently NULL - not available) |
| winner_name | string | L1 winner name |
| winner_price | float | L1 winner price |
| num_bidders | int | Number of participating vendors |
| vendor_name | string | Vendor name |
| vendor_rank | string | Vendor rank (L1, L2, L3, ...) |
| vendor_price | float | Vendor quoted price |
| status_flag | string | Data quality flag |

**Status Flags:**
- `ok` - Clean record
- `unranked_vendor` - No financial bid submitted
- `possible_dup` - Potential duplicate vendor name
- `repeat_winner` - Won multiple bids
- `anomaly_*` - Data quality issues

---

## Pipeline Phases

1. **Phase 2:** Scrape listing pages (bid_id, category, buyer, quantity)
2. **Phase 3:** Drill into bid details (vendor evaluations, winner info)
3. **Phase 4:** Flatten nested vendor arrays to rows
4. **Phase 5:** Clean and normalize data
5. **Phase 6:** Generate insights report
6. **Phase 7:** Package and validate outputs

---

## Configuration

Edit `gemedge/config.py`:

```python
TARGET_ROWS = 30              # Number of bids to scrape
MAX_RETRIES = 3               # Retry attempts
PAGE_DELAY_MIN = 1.0          # Min delay between pages
PAGE_DELAY_MAX = 2.5          # Max delay between pages
HEADLESS = True               # Run browser in headless mode
```

---

## Resumability

The scraper saves progress after each page/bid to `checkpoints/progress.json`. If interrupted, it resumes from the last checkpoint automatically.

**Reset checkpoint:**
```bash
rm checkpoints/progress.json
```

---

## Output Files

### bids.csv
Flat CSV with 251 vendor-level rows, 13 columns (~72 KB)

### bids.json
Nested JSON with 38 bid objects (~67 KB)

### insights_report.md
Summary insights: competitive bidding, price gaps, repeat winners

### writeup.md
Technical write-up: approach, challenges, solutions (308 words)

---

## Troubleshooting

**ModuleNotFoundError:**
```bash
source gemedge/venv/bin/activate
pip install -r gemedge/requirements.txt
```

**No bids scraped:**
```bash
python gemedge/main.py --debug  # See browser
tail -100 output/run.log        # Check logs
```

**Navigation timeout:**
```python
# In config.py, increase:
MAX_RETRIES = 5
PAGE_DELAY_MIN = 2.0
```

**Checkpoint corrupted:**
```bash
mv checkpoints/progress.json checkpoints/backup.json
python gemedge/main.py
```

---

## Technical Details

**Technologies:**
- Playwright 1.40.0 - Browser automation
- BeautifulSoup4 4.12.2 - HTML parsing
- pandas 2.1.3 - Data processing
- rapidfuzz 3.5.2 - Fuzzy string matching

**Anti-Detection:**
- Bypasses DevTools detection
- Hides webdriver property
- Random delays between requests

**Performance:**
- Phase 2 (Scraping): 3-5 minutes
- Phase 3 (Drill-down): 2-3 minutes
- Phase 4-7 (Processing): <1 minute
- **Total:** 5-10 minutes

---

## Limitations

- Award dates not publicly available (field remains NULL)
- Some buyer details redacted in military/defense bids
- ~50% of vendors have null ranks (didn't submit financial bids - expected)
- Sequential processing (not parallel)
- Portal structure changes may break selectors

---

## License

For educational and research purposes. Ensure compliance with GeM portal's terms of service.

---

## Additional Resources

- **output/writeup.md** - Technical write-up (308 words)
- **output/insights_report.md** - Procurement insights
- **output/run.log** - Detailed execution logs
