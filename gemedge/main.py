"""Main orchestration entrypoint for the GemEdge scraping system."""

import argparse
import asyncio
import os
import sys
import time
from typing import List, Dict
import pandas as pd

# Add parent directory to sys.path to enable absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemedge.config import SETUP_OK_MSG, CHECKPOINT_PATH
from gemedge.logger import logger
from gemedge.scraper import run_scraping, run_drill_down

def verify_setup() -> bool:
    """Verify that the project directory structure and required files exist."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    required_dirs = [
        os.path.join(base_dir, "checkpoints"),
        os.path.join(base_dir, "data", "raw"),
        os.path.join(base_dir, "output")
    ]

    required_files = [
        os.path.join(base_dir, "config.py"),
        os.path.join(base_dir, "browser.py"),
        os.path.join(base_dir, "logger.py"),
        os.path.join(base_dir, "checkpointing.py"),
        os.path.join(base_dir, "scraper.py"),
        os.path.join(base_dir, "cleaner.py"),
        os.path.join(base_dir, "insights.py"),
        os.path.join(base_dir, "main.py"),
        os.path.join(base_dir, "requirements.txt"),
        os.path.join(base_dir, "README.md")
    ]

    for d in required_dirs:
        if not os.path.isdir(d):
            sys.stderr.write(f"Missing required directory: {d}\n")
            return False

    for f in required_files:
        if not os.path.isfile(f):
            sys.stderr.write(f"Missing required file: {f}\n")
            return False

    print(SETUP_OK_MSG)
    return True

async def execute_phase_2() -> List[Dict]:
    """Execute scraping Phase 2 and log performance metrics."""
    logger.info("Starting Phase 2: Filter Application & Listing-Level Extraction...")
    start_time = time.time()
    
    rows = await run_scraping()
    
    end_time = time.time()
    logger.info(f"Phase 2 finished. Extracted {len(rows)} records in {end_time - start_time:.2f} seconds.")
    
    if rows:
        logger.info("Sample extracted row:")
        logger.info(str(rows[0]))
    else:
        logger.warning("No rows extracted during Phase 2.")
        
    return rows

async def execute_phase_3() -> List[Dict]:
    """Execute Phase 3 drill-down winner extraction."""
    logger.info("Starting Phase 3: Drill-Down: Bid Result Page...")
    start_time = time.time()
    
    rows = await run_drill_down()
    
    end_time = time.time()
    logger.info(f"Phase 3 finished. Processed {len(rows)} records in {end_time - start_time:.2f} seconds.")
    
    completed = sum(1 for r in rows if r.get("winner_name") is not None)
    no_result = sum(1 for r in rows if r.get("status_flag") == "no_result")
    nav_error = sum(1 for r in rows if r.get("status_flag") == "nav_error")
    
    logger.info(f"Phase 3 Summary: Total: {len(rows)} | Completed: {completed} | No Result: {no_result} | Nav Error: {nav_error}")
    return rows

async def execute_phase_4() -> pd.DataFrame:
    """Execute Phase 4 flattening of bidder evaluation records."""
    logger.info("Starting Phase 4: Deep Extraction & Flatten Structure...")
    start_time = time.time()
    
    import pandas as pd
    from gemedge.checkpointing import load_checkpoint
    rows = load_checkpoint(CHECKPOINT_PATH)
    if not rows:
        logger.error("No checkpoint data found. Please run Phase 2 and Phase 3 first.")
        raise RuntimeError("Missing checkpoint data.")
        
    has_vendors = any("vendors" in r for r in rows)
    if not has_vendors:
        logger.warning("Vendors data not found in checkpoint. Automatically executing Phase 3 drill-down first...")
        rows = await run_drill_down()
        
    flattened_rows = []
    for row in rows:
        vendors = row.get("vendors", [])
        if not vendors:
            flat_row = {
                "bid_id": row.get("bid_id"),
                "category": row.get("category"),
                "buyer": row.get("buyer"),
                "buyer_name": row.get("buyer_name"),
                "buyer_state": row.get("buyer_state"),
                "buyer_organisation": row.get("buyer_organisation"),
                "buyer_office": row.get("buyer_office"),
                "quantity": row.get("quantity"),
                "bid_value": row.get("bid_value"),
                "bid_start_date": row.get("bid_start_date"),
                "bid_end_date": row.get("bid_end_date"),
                "bid_validity_days": row.get("bid_validity_days"),
                "bid_status": row.get("bid_status"),
                "contract_duration": row.get("contract_duration"),
                "winner_name": row.get("winner_name"),
                "winner_price": row.get("winner_price"),
                "num_bidders": row.get("num_bidders"),
                "vendor_name": None,
                "vendor_rank": None,
                "vendor_price": None,
                "status_flag": row.get("status_flag")
            }
            flattened_rows.append(flat_row)
        else:
            for vendor in vendors:
                flat_row = {
                    "bid_id": row.get("bid_id"),
                    "category": row.get("category"),
                    "buyer": row.get("buyer"),
                    "buyer_name": row.get("buyer_name"),
                    "buyer_state": row.get("buyer_state"),
                    "buyer_organisation": row.get("buyer_organisation"),
                    "buyer_office": row.get("buyer_office"),
                    "quantity": row.get("quantity"),
                    "bid_value": row.get("bid_value"),
                    "bid_start_date": row.get("bid_start_date"),
                    "bid_end_date": row.get("bid_end_date"),
                    "bid_validity_days": row.get("bid_validity_days"),
                    "bid_status": row.get("bid_status"),
                    "contract_duration": row.get("contract_duration"),
                    "winner_name": row.get("winner_name"),
                    "winner_price": row.get("winner_price"),
                    "num_bidders": row.get("num_bidders"),
                    "vendor_name": vendor.get("vendor_name"),
                    "vendor_rank": vendor.get("vendor_rank"),
                    "vendor_price": vendor.get("vendor_price"),
                    "status_flag": row.get("status_flag")
                }
                flattened_rows.append(flat_row)
                
    df = pd.DataFrame(flattened_rows)
    
    required_cols = [
        "bid_id", "category", "buyer",
        "buyer_name", "buyer_state", "buyer_organisation", "buyer_office",
        "quantity", "bid_value",
        "bid_start_date", "bid_end_date", "bid_validity_days",
        "bid_status", "contract_duration",
        "winner_name", "winner_price", "num_bidders", "vendor_name",
        "vendor_rank", "vendor_price", "status_flag"
    ]
    
    for col in required_cols:
        if col not in df.columns:
            df[col] = None
            
    df = df[required_cols]
    
    end_time = time.time()
    logger.info(f"Phase 4 finished. Flattened into {len(df)} vendor-bid rows in {end_time - start_time:.2f} seconds.")
    logger.info(f"DataFrame shape: {df.shape}")
    logger.info("DataFrame columns and non-null counts:")
    for col in df.columns:
        logger.info(f"  {col}: {df[col].notna().sum()} non-null values")
        
    return df

async def execute_phase_5() -> pd.DataFrame:
    """Execute Phase 5: Data Cleaning & Reliability Layer."""
    logger.info("Starting Phase 5: Data Cleaning & Reliability Layer...")
    start_time = time.time()
    
    from gemedge.checkpointing import load_checkpoint
    from gemedge.cleaner import clean_data
    from gemedge.config import OUTPUT_DIR
    
    rows = load_checkpoint(CHECKPOINT_PATH)
    if not rows:
        logger.error("No checkpoint data found. Please run Phase 2 and Phase 3 first.")
        raise RuntimeError("Missing checkpoint data.")
        
    df = clean_data(rows)
    
    # Save the cleaned DataFrame to output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, "cleaned_bids.csv")
    df.to_csv(output_file, index=False)
    logger.info(f"Cleaned dataset saved to {output_file}")
    
    end_time = time.time()
    logger.info(f"Phase 5 finished in {end_time - start_time:.2f} seconds.")
    logger.info(f"Cleaned DataFrame Shape: {df.shape}")
    
    print("\n--- Cleaned DataFrame dtypes ---")
    print(df.dtypes)
    
    print("\n--- Cleaned DataFrame status_flag value counts ---")
    print(df["status_flag"].value_counts(dropna=False))
    print("-" * 50 + "\n")
    
    return df

async def execute_phase_6() -> None:
    """Execute Phase 6: Summary Insights generation."""
    logger.info("Starting Phase 6: Summary Insights...")
    start_time = time.time()
    
    df = await execute_phase_5()
    
    from gemedge.insights import generate_insights
    generate_insights(df)
    
    end_time = time.time()
    logger.info(f"Phase 6 finished in {end_time - start_time:.2f} seconds.")

async def execute_phase_7() -> None:
    """Execute Phase 7: Output Packaging & Validation."""
    logger.info("Starting Phase 7: Output Packaging & Validation...")
    start_time = time.time()
    
    df = await execute_phase_5()
    
    from gemedge.checkpointing import load_checkpoint
    from gemedge.config import CHECKPOINT_PATH
    raw_checkpoint_rows = load_checkpoint(CHECKPOINT_PATH)
    if not raw_checkpoint_rows:
        logger.error("No checkpoint data found. Please run Phase 2 and Phase 3 first.")
        raise RuntimeError("Missing checkpoint data.")
        
    from gemedge.packaging import package_and_validate
    package_and_validate(df, raw_checkpoint_rows)
    
    end_time = time.time()
    logger.info(f"Phase 7 finished in {end_time - start_time:.2f} seconds.")

async def run_orchestrator(args: argparse.Namespace) -> None:
    """Run specified scraping/processing phases based on command line arguments."""
    start_time = time.time()
    logger.info("Initializing GemEdge orchestrator run...")

    if args.debug:
        # Override headless flag in config at runtime
        import gemedge.config as cfg
        cfg.HEADLESS = False
        logger.info("Debug mode enabled: running in headful browser mode with slow-mo settings.")

    # Execute phases
    try:
        if args.phase == 2:
            await execute_phase_2()
        elif args.phase == 3:
            await execute_phase_3()
        elif args.phase == 4:
            await execute_phase_4()
        elif args.phase == 5:
            await execute_phase_5()
        elif args.phase == 6:
            await execute_phase_6()
        elif args.phase == 7:
            await execute_phase_7()
        else:
            # Run all phases sequentially
            logger.info("No specific phase requested. Running full workflow...")
            await execute_phase_2()
            await execute_phase_3()
            await execute_phase_4()
            await execute_phase_5()
            await execute_phase_6()
            await execute_phase_7()
            
    except Exception as e:
        logger.error(f"Orchestrator failed during execution: {e}", exc_info=True)
        sys.exit(1)

    end_time = time.time()
    logger.info(f"Total GemEdge run completed in {end_time - start_time:.2f} seconds.")

def main() -> None:
    """Parse command line arguments and launch orchestrator run."""
    parser = argparse.ArgumentParser(description="GemEdge Scraping Orchestrator")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify directories and required files exist"
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[2, 3, 4, 5, 6, 7],
        help="Run a specific phase of the workflow"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run scraper in non-headless mode with slow-mo execution"
    )

    args = parser.parse_args()

    if args.check:
        if verify_setup():
            sys.exit(0)
        else:
            sys.exit(1)

    # Launch orchestrator
    asyncio.run(run_orchestrator(args))

if __name__ == "__main__":
    main()
