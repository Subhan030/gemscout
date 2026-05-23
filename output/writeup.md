# GemEdge: GeM Portal Bid Data Extraction

## Approach

GemEdge automates extraction of awarded bid data from India's Government e-Marketplace (GeM) portal using a multi-phase pipeline. The scraper applies filters for awarded bids, extracts listing-level metadata (bid ID, category, buyer, quantity), drills into result pages for vendor evaluations, and flattens nested structures into a 13-column vendor-per-row dataset.

## Tools & Technologies

Built with Python 3.9+, Playwright for browser automation, BeautifulSoup for HTML parsing, and pandas for data processing. RapidFuzz handles fuzzy vendor name matching across technical and financial evaluation tables.

## Key Challenges & Solutions

**Anti-bot protections**: GeM uses DevTools detection scripts. Solution: Injected JavaScript to neutralize `DisableDevtool` and masked WebDriver flags before page load.

**Table structure inconsistencies**: Technical and financial tables vary in column order and header naming. Solution: Built adaptive parsers using CSS selectors and regex patterns, identifying tables by header keywords rather than fixed positions.

**Vendor name mismatches**: Names differ between tables due to legal suffixes and spacing variations. Solution: Normalized names by stripping suffixes (Pvt Ltd, LLP) and used RapidFuzz with 90% similarity threshold for matching.

**Pagination detection**: Standard `wait_for_load_state` failed to detect page transitions. Solution: Monitored changes in the "Total Records" text element to confirm navigation.

## Failure Handling

Three-tier retry logic with exponential backoff handles network failures. Navigation errors are flagged with `status_flag: nav_error` rather than halting execution. Checkpoint system saves progress after each page, enabling resume from interruption.

## Anomaly Detection

Automated flags identify data quality issues: `anomaly_winner_not_l1` (winner price exceeds L2), `anomaly_count_mismatch` (vendor count differs from num_bidders), `possible_dup` (duplicate vendor names), `unranked_vendor` (vendors without financial rank), and `repeat_winner` (multiple wins).

## Vulnerabilities & Limitations

Award dates are not publicly exposed—only submission deadlines are available, leaving `award_date` empty across all records. Redacted buyer details in military/defense bids remain inaccessible. Rate limiting is passive (1-2.5s delays); aggressive scraping may trigger IP blocks.
