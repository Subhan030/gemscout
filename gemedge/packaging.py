"""Packaging and validation module for the GemEdge scraper final deliverables."""

import os
import json
import pandas as pd
from gemedge.logger import logger
from gemedge.config import (
    RAW_DATA_DIR,
    INSIGHTS_REPORT_PATH,
    BIDS_CSV_PATH,
    BIDS_JSON_PATH,
    WRITEUP_PATH,
    RUN_LOG_PATH
)
from gemedge.cleaner import normalize_name

# Flat DataFrame required schema columns — must match config.REQUIRED_COLUMNS
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
    "status_flag"
]

def package_and_validate(df: pd.DataFrame, raw_checkpoint_rows: list[dict]) -> None:
    """Export the dataset to CSV and JSON, and run data quality assertions."""
    logger.info("Starting Phase 7 packaging and validation...")

    if df.empty:
        raise ValueError("DataFrame is empty. Cannot package empty data.")

    # 1. Export CSV
    df.to_csv(BIDS_CSV_PATH, index=False, encoding="utf-8-sig")
    logger.info(f"Successfully exported flat bids dataset to {BIDS_CSV_PATH}")

    # 2. Reconstruct and export nested JSON
    # Map (bid_id, normalized_vendor_name) -> (disqualified, remarks)
    vendor_extra = {}
    for row in raw_checkpoint_rows:
        bid_id = row.get("bid_id")
        for v in row.get("vendors", []):
            raw_vname = v.get("vendor_name")
            if raw_vname:
                v_name_norm = normalize_name(raw_vname)
                vendor_extra[(bid_id, v_name_norm)] = {
                    "disqualified": v.get("disqualified", False),
                    "remarks": v.get("remarks", "")
                }

    nested_bids = []
    seen_bids = set()
    for row in raw_checkpoint_rows:
        bid_id = row.get("bid_id")
        if not bid_id or bid_id in seen_bids:
            continue
        seen_bids.add(bid_id)

        bid_df = df[df["bid_id"] == bid_id]
        if bid_df.empty:
            continue

        first_row = bid_df.iloc[0]

        # Handle NaNs and convert nullable types safely
        quantity_val = int(first_row["quantity"]) if not pd.isna(first_row["quantity"]) else None
        bid_value_val = float(first_row["bid_value"]) if not pd.isna(first_row["bid_value"]) else None
        winner_price_val = float(first_row["winner_price"]) if not pd.isna(first_row["winner_price"]) else None
        num_bidders_val = int(first_row["num_bidders"]) if not pd.isna(first_row["num_bidders"]) else None

        award_date_str = None
        if not pd.isna(first_row["award_date"]):
            award_date_str = first_row["award_date"].strftime("%Y-%m-%d")

        bid_obj = {
            "bid_id": bid_id,
            "category": first_row["category"] if not pd.isna(first_row["category"]) else None,
            "buyer": first_row["buyer"] if not pd.isna(first_row["buyer"]) else None,
            "quantity": quantity_val,
            "bid_value": bid_value_val,
            "award_date": award_date_str,
            "winner_name": first_row["winner_name"] if not pd.isna(first_row["winner_name"]) else None,
            "winner_price": winner_price_val,
            "num_bidders": num_bidders_val,
            "status_flag": first_row["status_flag"] if not pd.isna(first_row["status_flag"]) else None,
            "vendors": []
        }

        # Populate vendors list
        for _, v_row in bid_df.iterrows():
            v_name = v_row["vendor_name"]
            if pd.isna(v_name):
                continue

            extra = vendor_extra.get((bid_id, v_name), {"disqualified": False, "remarks": ""})
            v_price_val = float(v_row["vendor_price"]) if not pd.isna(v_row["vendor_price"]) else None

            v_obj = {
                "vendor_name": v_name,
                "vendor_rank": v_row["vendor_rank"] if not pd.isna(v_row["vendor_rank"]) else None,
                "vendor_price": v_price_val,
                "disqualified": bool(extra["disqualified"]),
                "remarks": str(extra["remarks"])
            }
            bid_obj["vendors"].append(v_obj)

        nested_bids.append(bid_obj)

    with open(BIDS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(nested_bids, f, indent=2, ensure_ascii=False)
    logger.info(f"Successfully exported nested bids dataset to {BIDS_JSON_PATH}")

    # 3. Validation assertions
    logger.info("Executing data quality validation assertions...")
    assert len(df) >= 30, f"Validation Failed: Less than 30 rows in flat dataset (got {len(df)})"
    assert set(REQUIRED_COLUMNS) == set(df.columns), f"Validation Failed: Column mismatch. Got: {list(df.columns)}"
    assert df["bid_id"].nunique() >= 30, f"Validation Failed: Less than 30 unique bids (got {df['bid_id'].nunique()})"
    assert df["bid_id"].notna().all(), "Validation Failed: Null bid_ids detected in dataset."

    unique_winners_count = df.dropna(subset=["winner_name"]).drop_duplicates("bid_id")["bid_id"].nunique()
    assert unique_winners_count >= 25, f"Validation Failed: Too many missing winner names (got {unique_winners_count} unique, expected >=25)"

    logger.info("Data quality validation assertions passed successfully.")

    # 4. Final checklist verification
    logger.info("Verifying deliverables checklist...")
    checklist_items = {
        "output/bids.csv": BIDS_CSV_PATH,
        "output/bids.json": BIDS_JSON_PATH,
        "output/insights_report.md": INSIGHTS_REPORT_PATH,
        "output/writeup.md": WRITEUP_PATH,
        "output/run.log": RUN_LOG_PATH
    }

    for name, path in checklist_items.items():
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Checklist error: Required deliverable '{name}' is missing.")
        if os.path.getsize(path) == 0:
            raise ValueError(f"Checklist error: Deliverable '{name}' is empty.")

    # Raw evaluation HTML files check
    if not os.path.isdir(RAW_DATA_DIR):
        raise FileNotFoundError(f"Checklist error: Raw data directory '{RAW_DATA_DIR}' is missing.")
    raw_files = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".html")]
    if not raw_files:
        raise ValueError(f"Checklist error: Raw data directory '{RAW_DATA_DIR}' contains no evaluation HTML files.")

    logger.info(f"Checklist verified. {len(raw_files)} raw evaluation HTML files confirmed.")
    logger.info("Phase 7 packaging and validation completed successfully.")
