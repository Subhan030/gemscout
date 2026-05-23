"""Data cleaning and validation module for the scraped bid dataset."""

import re
import pandas as pd
from gemedge.logger import logger

def strip_suffixes(name) -> str:
    """Strip legal suffixes and helper tags from vendor names for deduplication."""
    if pd.isna(name) or name is None:
        return ""
    # lower case for comparison/regex
    s = str(name).lower().strip()
    # Strip "under pma"
    s = re.sub(r'\bunder\s+pma\b', '', s)
    # Suffixes
    s = re.sub(r'\b(private\s+limited|pvt\s+ltd|pvt\s+limited|pvt\.?\s*ltd\.?|ltd\.?|limited|llp|l\.l\.p\.|&?\s*co\.?|inc|corp|corporation)\b', '', s)
    # Remove trailing punctuation and spaces
    s = re.sub(r'[\s,\.\-\&]+$', '', s)
    s = re.sub(r'^[\s,\.\-\&]+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def normalize_name(name):
    """Normalize whitespace and apply title casing to vendor names."""
    if pd.isna(name) or name is None:
        return pd.NA
    s = str(name).strip()
    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s)
    # Convert to Title Case
    s = s.title()
    return s

def clean_numeric_column(series: pd.Series) -> pd.Series:
    """Coerce a series to float, stripping currency symbols and handling placeholders."""
    s = series.astype(str).str.strip()
    # Replace common placeholder values with NA
    placeholders = ['NIL', 'N/A', 'NA', '-', '', 'NONE', 'NULL', '<NA>', 'NAN']
    s_upper = s.str.upper()
    is_placeholder = s_upper.isin(placeholders) | series.isna()
    
    # Clean currency signs, commas, extra whitespace
    cleaned = s.str.replace(r'[₹\s,]|Rs\.?|INR', '', regex=True)
    
    # Convert to numeric
    coerced = pd.to_numeric(cleaned, errors='coerce')
    
    # Cast to pandas nullable Float64
    result = coerced.astype('Float64')
    result = result.mask(is_placeholder, pd.NA)
    
    originally_valid = ~(series.isna() | is_placeholder)
    coercion_failed = originally_valid & result.isna()
    if coercion_failed.any():
        failed_samples = series[coercion_failed].unique()
        logger.warning(f"Numeric coercion failed for values: {failed_samples}")
        
    return result

def clean_integer_column(series: pd.Series) -> pd.Series:
    """Coerce a series to nullable Int64, handling placeholders."""
    s = series.astype(str).str.strip()
    placeholders = ['NIL', 'N/A', 'NA', '-', '', 'NONE', 'NULL', '<NA>', 'NAN']
    s_upper = s.str.upper()
    is_placeholder = s_upper.isin(placeholders) | series.isna()
    
    cleaned = s.str.replace(r'[₹\s,]|Rs\.?|INR', '', regex=True)
    coerced = pd.to_numeric(cleaned, errors='coerce')
    result = coerced.astype('Int64')
    result = result.mask(is_placeholder, pd.NA)
    
    originally_valid = ~(series.isna() | is_placeholder)
    coercion_failed = originally_valid & result.isna()
    if coercion_failed.any():
        failed_samples = series[coercion_failed].unique()
        logger.warning(f"Integer coercion failed for values: {failed_samples}")
        
    return result

def parse_date_column(series: pd.Series) -> pd.Series:
    """Parse award date into datetime64[ns], trying multiple formats."""
    s = series.astype(str).str.strip()
    formats = ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d']
    
    parsed = pd.Series(pd.NaT, index=series.index, dtype='datetime64[ns]')
    
    placeholders = ['NIL', 'N/A', 'NA', '-', '', 'NONE', 'NULL', '<NA>', 'NAN']
    is_placeholder = s.str.upper().isin(placeholders) | series.isna()
    
    to_parse = s[~is_placeholder]
    
    for fmt in formats:
        still_null = parsed[~is_placeholder].isna()
        if not still_null.any():
            break
        try:
            temp = pd.to_datetime(to_parse[still_null], format=fmt, errors='coerce')
            parsed.loc[temp.dropna().index] = temp.dropna()
        except Exception:
            pass
            
    still_null = parsed[~is_placeholder].isna()
    if still_null.any():
        try:
            temp = pd.to_datetime(to_parse[still_null], errors='coerce')
            parsed.loc[temp.dropna().index] = temp.dropna()
        except Exception:
            pass
            
    originally_valid = ~(series.isna() | is_placeholder)
    failed_dates = originally_valid & parsed.isna()
    if failed_dates.any():
        failed_samples = series[failed_dates].unique()
        logger.warning(f"Date parsing failed for {failed_dates.sum()} values. Samples: {failed_samples}")
        
    return parsed

def find_vendor_duplicates(df: pd.DataFrame) -> set[str]:
    """Find vendor names that are duplicates of a more frequent vendor name using RapidFuzz."""
    vendor_series = df["vendor_name"].dropna()
    if vendor_series.empty:
        return set()
        
    normalized_names = vendor_series.unique()
    freq_map = vendor_series.value_counts().to_dict()
    stripped_map = {name: strip_suffixes(name) for name in normalized_names}
    
    from rapidfuzz import fuzz
    flagged = set()
    n = len(normalized_names)
    
    for i in range(n):
        name_a = normalized_names[i]
        strip_a = stripped_map[name_a]
        freq_a = freq_map.get(name_a, 0)
        
        for j in range(i + 1, n):
            name_b = normalized_names[j]
            strip_b = stripped_map[name_b]
            freq_b = freq_map.get(name_b, 0)
            
            if not strip_a or not strip_b:
                continue
                
            sim = fuzz.ratio(strip_a, strip_b)
            if sim > 90:
                if freq_a < freq_b:
                    flagged.add(name_a)
                elif freq_b < freq_a:
                    flagged.add(name_b)
                else:
                    # alphabetical tie breaker
                    if name_a > name_b:
                        flagged.add(name_a)
                    else:
                        flagged.add(name_b)
                        
    return flagged

def clean_data(raw_data: list[dict]) -> pd.DataFrame:
    """Clean, format, and validate the scraped raw bid records."""
    logger.info("Starting clean_data process...")
    
    # 1. Load raw data (support both nested list, flat list, and DataFrame)
    if isinstance(raw_data, list):
        has_nested = any("vendors" in r for r in raw_data if isinstance(r, dict))
        if has_nested:
            logger.info("Nested structure detected in raw data. Flattening vendors...")
            flattened_rows = []
            for row in raw_data:
                vendors = row.get("vendors", [])
                if not vendors:
                    flat_row = {
                        "bid_id": row.get("bid_id"),
                        "category": row.get("category"),
                        "buyer": row.get("buyer"),
                        "quantity": row.get("quantity"),
                        "bid_value": row.get("bid_value"),
                        "award_date": row.get("award_date"),
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
                            "quantity": row.get("quantity"),
                            "bid_value": row.get("bid_value"),
                            "award_date": row.get("award_date"),
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
        else:
            df = pd.DataFrame(raw_data)
    elif isinstance(raw_data, pd.DataFrame):
        df = raw_data.copy()
    else:
        raise TypeError("raw_data must be a list of dicts or a pandas DataFrame")

    required_cols = [
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
    
    # Initialize missing required columns to pd.NA
    for col in required_cols:
        if col not in df.columns:
            df[col] = pd.NA

    # 2. Numeric Coercion
    logger.info("Coercing numeric columns...")
    df['bid_value'] = clean_numeric_column(df['bid_value'])
    df['winner_price'] = clean_numeric_column(df['winner_price'])
    df['vendor_price'] = clean_numeric_column(df['vendor_price'])
    df['quantity'] = clean_numeric_column(df['quantity'])
    df['num_bidders'] = clean_integer_column(df['num_bidders'])

    # 3. Date Parsing
    logger.info("Parsing dates...")
    df['award_date'] = parse_date_column(df['award_date'])

    # 4. Vendor Name Normalization & Deduplication
    logger.info("Normalizing vendor names...")
    df['_raw_winner_name'] = df['winner_name']
    df['_raw_vendor_name'] = df['vendor_name']
    
    df['winner_name'] = df['winner_name'].apply(normalize_name)
    df['vendor_name'] = df['vendor_name'].apply(normalize_name)
    
    logger.info("Running RapidFuzz vendor name deduplication...")
    duplicate_names = find_vendor_duplicates(df)
    logger.info(f"Found {len(duplicate_names)} duplicate vendor name(s) to flag.")
    
    # Set status_flag to possible_dup only if currently "ok"
    is_ok = df['status_flag'] == 'ok'
    is_dup = df['vendor_name'].isin(duplicate_names)
    df.loc[is_ok & is_dup, 'status_flag'] = 'possible_dup'

    # 4b. Flag unranked vendors — vendors with null vendor_rank and no other flag
    logger.info("Flagging unranked vendors...")
    is_still_ok = df['status_flag'] == 'ok'
    has_vendor_name = df['vendor_name'].notna()
    rank_is_null = df['vendor_rank'].isna()
    df.loc[is_still_ok & has_vendor_name & rank_is_null, 'status_flag'] = 'unranked_vendor'
    logger.info(
        f"Flagged {(df['status_flag'] == 'unranked_vendor').sum()} rows as 'unranked_vendor'."
    )

    # 5. Anomaly Flagging
    logger.info("Checking for anomalies...")
    for bid_id, group in df.groupby('bid_id'):
        vendor_rows_count = group['vendor_name'].dropna().nunique()
        
        num_bidders_val = group['num_bidders'].dropna().first_valid_index()
        num_bidders = group.loc[num_bidders_val, 'num_bidders'] if num_bidders_val is not None else pd.NA
        
        winner_price_val = group['winner_price'].dropna().first_valid_index()
        winner_price = group.loc[winner_price_val, 'winner_price'] if winner_price_val is not None else pd.NA
        
        bid_value_val = group['bid_value'].dropna().first_valid_index()
        bid_value = group.loc[bid_value_val, 'bid_value'] if bid_value_val is not None else pd.NA
        
        # L2 Price calculation — only consider ranked vendors (non-null rank)
        ranked_group = group[group["vendor_rank"].notna() & (group["vendor_rank"].astype(str).str.strip() != "")]
        l2_rows = ranked_group[ranked_group["vendor_rank"].astype(str).str.upper().str.strip() == "L2"]
        l2_prices = l2_rows["vendor_price"].dropna()
        if not l2_prices.empty:
            l2_price = l2_prices.iloc[0]
        else:
            # Fallback: second-lowest price among ranked vendors
            ranked_prices = ranked_group["vendor_price"].dropna().unique()
            ranked_prices = sorted(ranked_prices)
            if len(ranked_prices) >= 2:
                l2_price = ranked_prices[1]
            else:
                l2_price = pd.NA
                
        anomaly_flag = None
        
        # Check winner_price > L2_price
        if not pd.isna(winner_price) and not pd.isna(l2_price) and winner_price > l2_price:
            anomaly_flag = "anomaly_winner_not_l1"
        # Check num_bidders != vendor_rows_count
        elif not pd.isna(num_bidders) and vendor_rows_count != int(num_bidders):
            anomaly_flag = "anomaly_count_mismatch"
        # Check winner_price > bid_value
        elif not pd.isna(bid_value) and not pd.isna(winner_price) and winner_price > bid_value:
            anomaly_flag = "anomaly_price_exceeds_bid"
            
        if anomaly_flag:
            ok_idx = group[group['status_flag'] == 'ok'].index
            df.loc[ok_idx, 'status_flag'] = anomaly_flag

    # Check for repeat winners
    logger.info("Running repeat winner detection...")
    winner_bids = df.dropna(subset=["winner_name"]).drop_duplicates(subset=["bid_id", "winner_name"])
    winner_counts = winner_bids["winner_name"].value_counts()
    repeat_winners = set(winner_counts[winner_counts > 1].index)
    logger.info(f"Found {len(repeat_winners)} repeat winner(s).")
    
    is_repeat_winner = df['winner_name'].isin(repeat_winners)
    
    def append_repeat_winner(flag):
        if pd.isna(flag) or flag == "":
            return "repeat_winner"
        if "repeat_winner" in str(flag):
            return flag
        return f"{flag}, repeat_winner"
        
    df.loc[is_repeat_winner, 'status_flag'] = df.loc[is_repeat_winner, 'status_flag'].apply(append_repeat_winner)

    # 6. Enforce final schema & log null-counts
    temp_cols = [c for c in df.columns if c.startswith('_')]
    df = df.drop(columns=temp_cols)
    
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' is missing from the cleaned DataFrame.")
            
    df = df[required_cols]
    
    logger.info("Cleaned DataFrame column non-null counts:")
    for col in df.columns:
        non_null_count = df[col].notna().sum()
        null_count = df[col].isna().sum()
        logger.info(f"  {col}: {non_null_count} non-null, {null_count} null/NA")
        
    logger.info("clean_data process finished successfully.")
    return df

