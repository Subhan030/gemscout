"""Web scraping module for extraction of tender/bid data."""

import asyncio
import os
import random
import re
from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
from playwright.async_api import Page
from rapidfuzz import fuzz

from gemedge.config import (
    BASE_URL,
    FILTER_STATUS_CHECKBOX,
    FILTER_OUTCOME_CHECKBOX,
    SEARCH_BUTTON,
    BID_CARD_SELECTOR,
    PAGINATION_LINKS,
    PAGINATION_NEXT,
    TOTAL_RECORD_SELECTOR,
    BID_NO_HOVER_SELECTOR,
    START_DATE_SELECTOR,
    END_DATE_SELECTOR,
    JS_STATUS_TYPE_FILTER,
    JS_STATUS_FILTER,
    GEM_BASE_DOMAIN,
    TARGET_ROWS,
    MAX_RETRIES,
    PAGE_DELAY_MIN,
    PAGE_DELAY_MAX,
    CHECKPOINT_PATH,
    TECH_EVAL_PANEL,
    FIN_EVAL_PANEL,
    TECH_EVAL_LINK,
    FIN_EVAL_LINK,
    RAW_DATA_DIR
)
from gemedge.logger import logger
from gemedge.checkpointing import save_checkpoint, load_checkpoint
from gemedge.browser import get_browser


def parse_card(card_soup: BeautifulSoup) -> Dict:
    """Parse a BS4 card element and extract listing-level fields."""
    # Extract Bid/RA numbers
    bid_links = card_soup.select(BID_NO_HOVER_SELECTOR)
    bid_id = ""
    if bid_links:
        bid_id = bid_links[0].text.strip()

    # Extract Category (Items field)
    items_strong = card_soup.find("strong", string=lambda s: s and "Items:" in s)
    category = ""
    if items_strong:
        parent = items_strong.parent
        link = parent.find("a")
        if link and link.get("data-content"):
            category = link.get("data-content").strip()
        else:
            category = parent.text.replace("Items:", "").strip()
    # Normalize spaces in category
    category = " ".join(category.split())

    # Extract Buyer (Department Name and Address)
    buyer_strong = card_soup.find("strong", string=lambda s: s and "Department Name And Address:" in s)
    buyer = ""
    if buyer_strong:
        container = buyer_strong.find_parent("div", class_="col-md-5")
        if container:
            rows = container.select(".row")
            if len(rows) > 1:
                buyer = " ".join([line.strip() for line in rows[1].text.split("\n") if line.strip()])
            else:
                buyer = container.text.replace("Department Name And Address:", "").strip()
        else:
            buyer = buyer_strong.parent.text.replace("Department Name And Address:", "").strip()
    buyer = " ".join(buyer.split())

    # Extract Quantity
    qty_strong = card_soup.find("strong", string=lambda s: s and "Quantity:" in s)
    quantity = ""
    if qty_strong:
        quantity = qty_strong.parent.text.replace("Quantity:", "").strip()

    # Extract Detail URL & RA Detail URL
    detail_url = ""
    ra_detail_url = None
    links = card_soup.find_all("a", href=True)
    for link in links:
        href = link.get("href")
        btn = link.find("input")
        btn_val = btn.get("value", "") if btn else ""
        link_text = link.text.strip()
        
        is_result_link = False
        if "result" in btn_val.lower() or "result" in link_text.lower():
            is_result_link = True
        elif "view" in btn_val.lower() or "view" in link_text.lower():
            is_result_link = True
        elif "bidding/bid/" in href:
            is_result_link = True
            
        if is_result_link:
            full_url = href if href.startswith("http") else f"{GEM_BASE_DOMAIN}{href}"
            if "ra" in btn_val.lower() or "ra" in link_text.lower():
                ra_detail_url = full_url
            else:
                detail_url = full_url

    return {
        "bid_id": bid_id,
        "category": category,
        "buyer": buyer,
        "quantity": quantity,
        "bid_value": None,
        "award_date": None,
        "detail_url": detail_url,
        "ra_detail_url": ra_detail_url
    }

async def detect_total_pages(page: Page) -> int:
    """Detect the total number of pages from the pagination elements on the page."""
    try:
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        links = soup.select(PAGINATION_LINKS)
        page_numbers = []
        for link in links:
            text = link.text.strip()
            if text.isdigit():
                page_numbers.append(int(text))
        if page_numbers:
            return max(page_numbers)
    except Exception as e:
        logger.error(f"Failed to detect total pages: {e}")
    return 1

async def wait_for_page_transition(page: Page, old_record_text: str) -> bool:
    """Wait for the record count text to update after navigating to the next page."""
    for _ in range(20):
        try:
            content = await page.content()
            soup = BeautifulSoup(content, "lxml")
            elem = soup.select_one(TOTAL_RECORD_SELECTOR)
            if elem:
                new_text = elem.text.strip()
                if new_text != old_record_text:
                    return True
        except Exception as e:
            logger.debug(f"Error checking page transition: {e}")
        await asyncio.sleep(0.5)
    return False

async def apply_filters_with_retry(page: Page) -> None:
    """Navigate to BASE_URL and apply status and outcome filters with retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Navigating to {BASE_URL} (Attempt {attempt})...")
            await page.goto(BASE_URL, wait_until="networkidle")
            
            # Wait for filter options to load (inputs are styled and hidden, so check for attachment)
            logger.debug("Waiting for filter elements...")
            await page.wait_for_selector(FILTER_STATUS_CHECKBOX, state="attached", timeout=10000)
            await page.wait_for_selector(FILTER_OUTCOME_CHECKBOX, state="attached", timeout=10000)
            
            # Apply filters via JS evaluation
            logger.info("Applying status and outcome filters...")
            await page.evaluate(f"() => {{ {JS_STATUS_TYPE_FILTER}; }}")
            await asyncio.sleep(1.0)
            await page.evaluate(f"() => {{ {JS_STATUS_FILTER}; }}")
            await asyncio.sleep(1.0)
            
            # Submit search
            logger.debug("Clicking search button...")
            await page.click(SEARCH_BUTTON)
            await page.wait_for_load_state("networkidle")
            
            # Wait for cards to load
            await page.wait_for_selector(BID_CARD_SELECTOR, timeout=15000)
            logger.info("Filters applied successfully and first page cards loaded.")
            return
        except Exception as e:
            logger.error(f"Attempt {attempt} to apply filters failed: {e}")
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Failed to apply filters after {MAX_RETRIES} attempts: {e}")
            await asyncio.sleep(5.0)

async def run_scraping() -> List[Dict]:
    """Execute the main web scraping phase and return raw extracted rows."""
    # Load existing checkpoint progress
    scraped_rows = load_checkpoint(CHECKPOINT_PATH)
    if len(scraped_rows) >= TARGET_ROWS:
        logger.info(f"Checkpoint already contains {len(scraped_rows)} bids (Target is {TARGET_ROWS}). Skipping scraping.")
        return scraped_rows

    scraped_ids = {row["bid_id"] for row in scraped_rows if row.get("bid_id")}
    logger.info(f"Resuming scraping session. Already scraped {len(scraped_ids)} unique bids.")

    async with get_browser() as (browser, page):
        # Inject anti-debugging bypass script
        await page.add_init_script("""
            Object.defineProperty(window, 'DisableDevtool', {
                value: function(options) {
                    console.log('Bypassed DisableDevtool initialization');
                },
                writable: false,
                configurable: false
            });
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Apply filters
        await apply_filters_with_retry(page)

        # Detect pagination
        total_pages = await detect_total_pages(page)
        logger.info(f"Found {total_pages} pages, targeting {TARGET_ROWS} total bids")

        page_num = 1
        while len(scraped_ids) < TARGET_ROWS and page_num <= total_pages:
            logger.info(f"Processing page {page_num} of {total_pages}...")
            
            # Scrape page contents with retry loop
            cards_loaded = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    await page.wait_for_selector(BID_CARD_SELECTOR, timeout=15000)
                    cards_loaded = True
                    break
                except Exception as e:
                    logger.warning(f"Attempt {attempt} failed to find cards on page {page_num}: {e}")
                    if attempt == MAX_RETRIES:
                        logger.error(f"All retries exhausted for page {page_num}. Skipping page.")
                        break
                    await asyncio.sleep(5.0)

            if not cards_loaded:
                # Increment page number and try to click next to recover/continue
                page_num += 1
                continue

            content = await page.content()
            soup = BeautifulSoup(content, "lxml")
            cards = soup.select(BID_CARD_SELECTOR)
            logger.info(f"Found {len(cards)} cards on page {page_num}")

            # Parse each card
            new_bids_scraped = 0
            for card in cards:
                try:
                    row = parse_card(card)
                    bid_id = row["bid_id"]
                    if not bid_id:
                        continue
                    if bid_id not in scraped_ids:
                        scraped_rows.append(row)
                        scraped_ids.add(bid_id)
                        new_bids_scraped += 1
                except Exception as e:
                    logger.error(f"Error parsing card on page {page_num}: {e}")

            logger.info(f"Scraped {new_bids_scraped} new bids from page {page_num}. Total unique: {len(scraped_ids)}")

            # Save checkpoint after every page
            save_checkpoint(scraped_rows, CHECKPOINT_PATH)

            if len(scraped_ids) >= TARGET_ROWS:
                logger.info(f"Reached target row count of {TARGET_ROWS} (Scraped {len(scraped_ids)}). Stopping.")
                break

            if page_num >= total_pages:
                logger.info("Reached the last page. Scraping complete.")
                break

            # Capture current record text for page transition check
            old_record_text = ""
            total_record_elem = soup.select_one(TOTAL_RECORD_SELECTOR)
            if total_record_elem:
                old_record_text = total_record_elem.text.strip()

            # Navigate to next page with retry
            next_clicked = False
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    logger.info(f"Navigating to next page (Attempt {attempt})...")
                    next_button = page.locator(PAGINATION_NEXT)
                    await next_button.click()
                    await page.wait_for_load_state("networkidle")
                    
                    # Wait for record text to change
                    transition_ok = await wait_for_page_transition(page, old_record_text)
                    if transition_ok:
                        next_clicked = True
                        break
                    else:
                        logger.warning(f"Page transition check failed on attempt {attempt}")
                except Exception as e:
                    logger.error(f"Failed to click next page button: {e}")
                
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(5.0)

            if not next_clicked:
                logger.error(f"Failed to transition to next page after page {page_num}. Stopping scraper.")
                break

            page_num += 1
            
            # Apply random delay jitter
            delay = random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
            logger.debug(f"Sleeping for {delay:.2f} seconds between pages...")
            await asyncio.sleep(delay)

    return scraped_rows

def normalize_name_for_matching(name: str) -> str:
    """Normalize vendor name to a standard format for string matching."""
    if not name:
        return ""
    # Strip any extra annotations like "Under PMA" or "under pma"
    name_clean = name.split("Under PMA")[0].split("under pma")[0].strip().upper()
    name_clean = " ".join(name_clean.split())
    # Remove punctuation, keeping only alphanumeric, spaces, and &
    name_clean = re.sub(r"[^\w\s&]", "", name_clean)
    name_clean = " ".join(name_clean.split())
    
    suffixes = [
        r"\bPRIVATE LIMITED\b", r"\bPVT LTD\b", r"\bPVT\b", r"\bLIMITED\b", r"\bLTD\b",
        r"\bLLP\b", r"\bPARTNERSHIP\b", r"\bCOMPANY\b", r"\bCO\b", r"\bINC\b", r"\bCORP\b"
    ]
    for pattern in suffixes:
        name_clean = re.sub(pattern, "", name_clean)
        
    name_clean = " ".join(name_clean.split())
    return name_clean

def extract_award_date_from_soup(soup: BeautifulSoup) -> Optional[str]:
    """Extract the award date from a result page's text."""
    text = soup.get_text(" ", strip=True)
    # Try to find award date patterns in the page
    # Common patterns: "Award Date: DD-MM-YYYY" or similar
    pattern = re.compile(
        r'(?:Award|Awarded)\s+(?:Date|On):\s*(\d{2}-\d{2}-\d{4})',
        re.IGNORECASE
    )
    m = pattern.search(text)
    if m:
        return m.group(1)  # Returns "DD-MM-YYYY"
    return None


def extract_evaluation_tables(soup: BeautifulSoup) -> Tuple[List[Dict], List[Dict]]:
    """Parse technical and financial evaluation tables from BeautifulSoup soup."""
    tech_list: List[Dict] = []
    fin_list: List[Dict] = []
    
    tables = soup.find_all("table")
    for table in tables:
        # Find headers
        headers = [th.text.strip().lower() for th in table.find_all("th")]
        if not headers:
            first_row = table.find("tr")
            if first_row:
                headers = [td.text.strip().lower() for td in first_row.find_all(["td", "th"])]
        
        # Check table type: Technical vs Financial
        is_tech = any("status" in h for h in headers) and not any("rank" in h for h in headers) and not any("total price" in h for h in headers)
        is_fin = any("rank" in h for h in headers)
        
        rows = table.find_all("tr")[1:]
        if is_tech:
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 5:
                    name = ""
                    seller_cell = row.find(class_="sellername")
                    if seller_cell:
                        name = seller_cell.text.strip()
                    else:
                        name = cells[1].text.strip()
                    
                    # Extract technical status from the Status column
                    status_text = ""
                    status_cell = None
                    for cell in cells[2:]:
                        txt = cell.text.strip()
                        if "qualified" in txt.lower() or "disqualified" in txt.lower():
                            status_text = txt
                            status_cell = cell
                            break
                    
                    if not status_text and len(cells) >= 5:
                        status_text = cells[-1].text.strip()
                        status_cell = cells[-1]
                    
                    # Determine if disqualified
                    disqualified = "disqualified" in status_text.lower()
                    
                    tech_list.append({
                        "vendor_name": name,
                        "disqualified": disqualified
                    })
        elif is_fin:
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    name = ""
                    seller_cell = row.find(class_="sellername")
                    if seller_cell:
                        name = seller_cell.text.strip()
                    else:
                        name = cells[1].text.strip()
                        
                    price = ""
                    price_cell = row.find(class_="bid_price")
                    if price_cell:
                        price = price_cell.text.strip()
                    elif len(cells) >= 4:
                        price = cells[3].text.strip()
                        
                    rank = ""
                    strong_tag = row.find("strong")
                    if strong_tag and ("l" in strong_tag.text.lower() or strong_tag.text.strip().isdigit()):
                        rank = strong_tag.text.strip()
                    elif len(cells) >= 5:
                        rank = cells[4].text.strip()
                    elif len(cells) >= 4:
                        rank = cells[-1].text.strip()
                        
                    fin_list.append({
                        "vendor_name": name,
                        "vendor_rank": rank,
                        "vendor_price": price
                    })
                    
    return tech_list, fin_list

def merge_vendor_evaluations(tech_list: List[Dict], fin_list: List[Dict]) -> List[Dict]:
    """Merge technical and financial evaluation lists by vendor name using string similarity."""
    merged: List[Dict] = []
    matched_fin_indices = set()
    
    for tech in tech_list:
        tech_name = tech["vendor_name"]
        norm_tech = normalize_name_for_matching(tech_name)
        
        best_match_idx = -1
        best_score = 0.0
        
        for idx, fin in enumerate(fin_list):
            if idx in matched_fin_indices:
                continue
            fin_name = fin["vendor_name"]
            norm_fin = normalize_name_for_matching(fin_name)
            
            if norm_tech == norm_fin:
                best_match_idx = idx
                best_score = 100.0
                break
            
            score = fuzz.ratio(norm_tech, norm_fin)
            if score > best_score:
                best_score = score
                best_match_idx = idx
                
        if best_match_idx != -1 and best_score >= 90.0:
            matched_fin_indices.add(best_match_idx)
            fin_match = fin_list[best_match_idx]
            merged.append({
                "vendor_name": tech_name,
                "vendor_rank": fin_match["vendor_rank"],
                "vendor_price": fin_match["vendor_price"],
                "disqualified": tech["disqualified"]
            })
        else:
            merged.append({
                "vendor_name": tech_name,
                "vendor_rank": None,
                "vendor_price": None,
                "disqualified": tech["disqualified"]
            })
            
    for idx, fin in enumerate(fin_list):
        if idx not in matched_fin_indices:
            merged.append({
                "vendor_name": fin["vendor_name"],
                "vendor_rank": fin["vendor_rank"],
                "vendor_price": fin["vendor_price"],
                "disqualified": False
            })
            
    return merged

async def run_drill_down() -> List[Dict]:
    """Execute Phase 3 & 4 drill-down extraction for all scraped bids."""
    scraped_rows = load_checkpoint(CHECKPOINT_PATH)
    if not scraped_rows:
        logger.warning("No bids loaded from checkpoint. Please run Phase 2 first.")
        return []

    rows_to_process = []
    for idx, row in enumerate(scraped_rows):
        if not row.get("winner_name") or row.get("status_flag") != "ok":
            rows_to_process.append((idx, row))

    if not rows_to_process:
        logger.info("All bids in checkpoint are already processed. Skipping drill-down.")
        return scraped_rows

    logger.info(f"Starting drill-down for {len(rows_to_process)} bids...")

    async with get_browser() as (browser, page):
        # Inject anti-debugging bypass script
        await page.add_init_script("""
            Object.defineProperty(window, 'DisableDevtool', {
                value: function(options) {
                    console.log('Bypassed DisableDevtool initialization');
                },
                writable: false,
                configurable: false
            });
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        for idx, row in rows_to_process:
            bid_id = row["bid_id"]
            detail_url = row.get("detail_url")
            ra_detail_url = row.get("ra_detail_url")
            
            logger.info(f"Processing bid {bid_id}...")
            
            # Apply random delay jitter
            delay = random.uniform(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
            logger.debug(f"Sleeping for {delay:.2f} seconds before navigating...")
            await asyncio.sleep(delay)
            
            tech_list: List[Dict] = []
            fin_list: List[Dict] = []
            status_flag = "ok"
            nav_error_occurred = False
            
            if ra_detail_url:
                logger.info(f"[{bid_id}] Navigating to RA detail URL: {ra_detail_url}...")
                try:
                    await page.goto(ra_detail_url, wait_until="networkidle")
                    try:
                        fin_link = page.locator(FIN_EVAL_LINK)
                        if await fin_link.count() > 0:
                            await fin_link.click()
                            await page.wait_for_selector(f"{FIN_EVAL_PANEL} table", timeout=5000)
                    except Exception as e:
                        logger.debug(f"[{bid_id}] Failed to click collapseThree or table not found: {e}")
                        
                    content = await page.content()
                    
                    os.makedirs(RAW_DATA_DIR, exist_ok=True)
                    safe_bid_id = bid_id.replace("/", "_")
                    ra_html_path = os.path.join(RAW_DATA_DIR, f"{safe_bid_id}_ra_eval.html")
                    with open(ra_html_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    soup = BeautifulSoup(content, "lxml")
                    _, sub_fin = extract_evaluation_tables(soup)
                    fin_list.extend(sub_fin)
                except Exception as e:
                    logger.error(f"[{bid_id}] Error loading RA detail URL {ra_detail_url}: {e}")
                    status_flag = "nav_error"
                    nav_error_occurred = True
                    
            if detail_url and not nav_error_occurred:
                logger.info(f"[{bid_id}] Navigating to Bid detail URL: {detail_url}...")
                try:
                    await page.goto(detail_url, wait_until="networkidle")
                    try:
                        tech_link = page.locator(TECH_EVAL_LINK)
                        if await tech_link.count() > 0:
                            await tech_link.click()
                            await page.wait_for_selector(f"{TECH_EVAL_PANEL} table", timeout=5000)
                    except Exception as e:
                        logger.debug(f"[{bid_id}] Failed to click collapseTwo or table not found: {e}")
                        
                    if not ra_detail_url:
                        try:
                            fin_link = page.locator(FIN_EVAL_LINK)
                            if await fin_link.count() > 0:
                                await fin_link.click()
                                await page.wait_for_selector(f"{FIN_EVAL_PANEL} table", timeout=5000)
                        except Exception as e:
                            logger.debug(f"[{bid_id}] Failed to click collapseThree or table not found: {e}")
                            
                    content = await page.content()
                    
                    os.makedirs(RAW_DATA_DIR, exist_ok=True)
                    safe_bid_id = bid_id.replace("/", "_")
                    suffix = "bid_eval" if ra_detail_url else "eval"
                    bid_html_path = os.path.join(RAW_DATA_DIR, f"{safe_bid_id}_{suffix}.html")
                    with open(bid_html_path, "w", encoding="utf-8") as f:
                        f.write(content)
                        
                    soup = BeautifulSoup(content, "lxml")
                    sub_tech, sub_fin = extract_evaluation_tables(soup)
                    tech_list.extend(sub_tech)
                    if not ra_detail_url:
                        fin_list.extend(sub_fin)
                except Exception as e:
                    logger.error(f"[{bid_id}] Error loading Bid detail URL {detail_url}: {e}")
                    status_flag = "nav_error"
                    nav_error_occurred = True

            if nav_error_occurred:
                row["winner_name"] = None
                row["winner_price"] = None
                row["num_bidders"] = None
                row["status_flag"] = "nav_error"
                row["vendors"] = []
            else:
                merged_vendors = merge_vendor_evaluations(tech_list, fin_list)

                # Extract award_date from the saved HTML file
                award_date_str = None
                _soup = None
                safe_bid_id = bid_id.replace("/", "_")
                for suffix in ("bid_eval", "ra_eval", "eval"):
                    candidate = os.path.join(RAW_DATA_DIR, f"{safe_bid_id}_{suffix}.html")
                    if os.path.isfile(candidate):
                        try:
                            with open(candidate, "r", encoding="utf-8") as _f:
                                _soup = BeautifulSoup(_f.read(), "lxml")
                            award_date_str = extract_award_date_from_soup(_soup)
                            if award_date_str:
                                break
                        except Exception:
                            pass
                row["award_date"] = award_date_str

                if not merged_vendors:
                    row["winner_name"] = None
                    row["winner_price"] = None
                    row["num_bidders"] = None
                    row["status_flag"] = "no_result"
                    row["vendors"] = []
                else:
                    l1_winner = None
                    for vendor in merged_vendors:
                        rank = vendor.get("vendor_rank")
                        if rank == "L1":
                            l1_winner = vendor
                            break

                    if l1_winner:
                        row["winner_name"] = l1_winner["vendor_name"]
                        row["winner_price"] = l1_winner["vendor_price"]
                        # Derive bid_value = winner_price * quantity when both are numeric
                        try:
                            wp = float(str(l1_winner["vendor_price"]).replace(",", ""))
                            qty = float(str(row.get("quantity", "")).replace(",", ""))
                            row["bid_value"] = wp * qty
                        except (TypeError, ValueError):
                            row["bid_value"] = None
                    else:
                        row["winner_name"] = None
                        row["winner_price"] = None
                        row["bid_value"] = None

                    row["num_bidders"] = len(merged_vendors)
                    row["status_flag"] = "ok"
                    row["vendors"] = merged_vendors

            scraped_rows[idx] = row
            save_checkpoint(scraped_rows, CHECKPOINT_PATH)
            logger.info(
                f"[{bid_id}] Saved progress: winner_name={row['winner_name']}, "
                f"award_date={row.get('award_date')}, bid_value={row.get('bid_value')}, "
                f"status_flag={row['status_flag']}"
            )
            
    return scraped_rows

