"""
Process MBP-10 .dbn files into a single front-month ZC parquet dataset.

Reads daily .dbn files from data/raw/MPB10_20250216-20260216, filters to front-month
corn (ZC) only, applies record validity and depth filters, and writes
data/processed/MBP10_ZC.parquet. Tracks processed days in
data/processed/MBP-10_ZC_days_processed.csv so the script can be re-run safely
when new daily files are added.
"""

import argparse
from pathlib import Path
import logging
from typing import Optional

import pandas as pd
import databento as db
from tqdm import tqdm

# paths 
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "MPB10_20250216-20260216"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PARQUET = PROCESSED_DIR / "MBP10_ZC.parquet"
DAYS_PROCESSED_CSV = PROCESSED_DIR / "MBP-10_ZC_days_processed.csv"

DBN_PATTERN = "glbx-mdp3-*.mbp-10.dbn"

# Columns to keep in output
COLUMNS_TO_KEEP = ["ts_event","action","side","depth","price","size","flags",
    "bid_px_00","ask_px_00","bid_sz_00","ask_sz_00","bid_ct_00","ask_ct_00",
    "bid_px_01","ask_px_01","bid_sz_01","ask_sz_01","bid_ct_01","ask_ct_01",
    "bid_px_02","ask_px_02","bid_sz_02","ask_sz_02","bid_ct_02","ask_ct_02",
    "bid_px_03","ask_px_03","bid_sz_03","ask_sz_03","bid_ct_03","ask_ct_03",
    "bid_px_04","ask_px_04","bid_sz_04","ask_sz_04","bid_ct_04","ask_ct_04",
    "bid_px_05","ask_px_05","bid_sz_05","ask_sz_05","bid_ct_05","ask_ct_05",
    "symbol"]

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)



#date and front month logic
def get_date_from_filepath(data_path: str) -> str:
    """Extract YYYYMMDD from path like .../glbx-mdp3-20250216.mbp-10.dbn."""
    prefix = "glbx-mdp3-"
    i = data_path.find(prefix)
    if i == -1:
        raise ValueError(f"path does not contain {prefix!r}: {data_path}")
    return data_path[i + len(prefix) : i + len(prefix) + 8]


def get_front_month(data_path: str) -> str:
    """
    CME ZC front-month for the file's date.
    Single year digit; roll on or after the 15th; months H,K,N,U,Z.
    """
    date_str = get_date_from_filepath(data_path)
    year = date_str[3] 
    month = int(date_str[4:6])
    day = int(date_str[6:8])

    if day >= 15:
        if month == 12:
            month = 1
            year = str(int(year) + 1)
        else:
            month += 1

    if month <= 3:
        front_month = "ZCH"
    elif month <= 5:
        front_month = "ZCK"
    elif month <= 7:
        front_month = "ZCN"
    elif month <= 9:
        front_month = "ZCU"
    else:
        front_month = "ZCZ"
    front_month += year
    return front_month


# filters, removing shit flags, non front month contracts, beyond level 5 orderbook
def is_valid_record(flags_series: pd.Series) -> pd.Series:
    """
    Valid iff: F_LAST set, not F_BAD_TS_RECV, not F_MAYBE_BAD_BOOK, not F_SNAPSHOT.
    Applied as (flags & 172) == 128.
    """
    return (flags_series & 172) == 128


def filter_and_select(df: pd.DataFrame, front_symbol: str) -> pd.DataFrame:
    """Filter to valid records, depth < 5, front-month symbol; keep only desired columns."""
    mask = (
        (df["symbol"] == front_symbol)
        & is_valid_record(df["flags"])
        & (df["depth"] < 5)
    )
    out = df.loc[mask].copy()
    existing = [c for c in COLUMNS_TO_KEEP if c in out.columns]
    missing = set(COLUMNS_TO_KEEP) - set(existing)
    if missing:
        logger.debug("columns not in data (may be schema-dependent): %s", missing)
    return out[existing]



# processing file iterative
def process_one_dbn(file_path: Path) -> Optional[pd.DataFrame]:
    """Load one .dbn, filter to front-month ZC with validity/depth filters; return subset of columns."""
    try:
        date_str = get_date_from_filepath(str(file_path))
        front_symbol = get_front_month(str(file_path))
    except ValueError as e:
        logger.warning("skip %s: %s", file_path.name, e)
        return None

    store = db.DBNStore.from_file(str(file_path))
    df = store.to_df()
    if df.empty:
        return None

    filtered = filter_and_select(df, front_symbol)
    if filtered.empty:
        return None
    return filtered


# track processed days
def load_processed_dates(csv_path: Path) -> set[str]:
    """Return set of YYYYMMDD dates already recorded in the tracking CSV."""
    if not csv_path.exists():
        return set()
    tab = pd.read_csv(csv_path)
    if "date" not in tab.columns:
        return set()
    return set(tab["date"].astype(str).str.replace(r"\-", "", regex=True).str[:8])


def append_processed_dates(csv_path: Path, new_dates: list[str]) -> None:
    """Append new YYYYMMDD dates to the tracking CSV."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    new_df = pd.DataFrame({"date": sorted(set(new_dates))})
    if csv_path.exists():
        existing = pd.read_csv(csv_path)
        combined = pd.concat([existing, new_df], ignore_index=True).drop_duplicates(subset=["date"])
        combined = combined.sort_values("date").reset_index(drop=True)
    else:
        combined = new_df.drop_duplicates().sort_values("date").reset_index(drop=True)
    combined.to_csv(csv_path, index=False)



# Main CONTROLLER !!!!      connect all it all.
def run(
    raw_dir: Optional[Path] = None,
    output_parquet: Optional[Path] = None,
    days_processed_csv: Optional[Path] = None,
) -> None:
    """
    Process all unprocessed .dbn files in raw_dir, merge with existing output,
    and update the processed-days CSV.
    """
    raw_dir = raw_dir or RAW_DIR
    output_parquet = output_parquet or OUTPUT_PARQUET
    days_processed_csv = days_processed_csv or DAYS_PROCESSED_CSV

    if not raw_dir.exists():
        raise FileNotFoundError(f"raw data directory not found: {raw_dir}")

    processed = load_processed_dates(days_processed_csv)
    all_files = sorted(raw_dir.glob(DBN_PATTERN))
    if not all_files:
        logger.warning("no .dbn files matching %s in %s", DBN_PATTERN, raw_dir)
        return

    #only process files whose date is not in csv
    to_process: list[Path] = []
    for f in all_files:
        try:
            date_str = get_date_from_filepath(str(f))
            if date_str not in processed:
                to_process.append(f)
        except ValueError:
            continue

    logger.info(
        "found %s .dbn files; %s already processed; %s to process",
        len(all_files),
        len(processed),
        len(to_process),
    )

    if not to_process:
        logger.info("nothing new to process")
        return

    #process files, new
    chunks: list[pd.DataFrame] = []
    newly_processed_dates: list[str] = []

    for file_path in tqdm(to_process, desc="processing .dbn"):
        date_str = get_date_from_filepath(str(file_path))
        df = process_one_dbn(file_path)
        if df is not None and not df.empty:
            chunks.append(df)
            newly_processed_dates.append(date_str)

    if not chunks:
        logger.info("no new data produced from %s file(s)", len(to_process))
        return

    # Align columns: use intersection of COLUMNS_TO_KEEP and what's in the new chunks
    common_cols = [c for c in COLUMNS_TO_KEEP if c in chunks[0].columns]
    chunks = [c[common_cols] for c in chunks]

    # load the parquet if it exists and prepend to combned outpyut
    if output_parquet.exists():
        existing_df = pd.read_parquet(output_parquet)
        existing_cols = [c for c in common_cols if c in existing_df.columns]
        if existing_cols != common_cols:
            logger.warning("existing parquet has different columns; using intersection")
        use_cols = [c for c in common_cols if c in existing_df.columns]
        existing_df = existing_df[use_cols]
        chunks = [existing_df] + [c[use_cols] for c in chunks]
    else:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        use_cols = common_cols

    combined = pd.concat(chunks, ignore_index=True)
    combined = combined.sort_values("ts_event").reset_index(drop=True)
    combined.to_parquet(output_parquet, index=False)
    logger.info("wrote %s rows to %s", len(combined), output_parquet)

    append_processed_dates(days_processed_csv, newly_processed_dates)
    logger.info("updated processed-days CSV with %s new date(s)", len(newly_processed_dates))


def main() -> None:
    parser = argparse.ArgumentParser(description="Process MBP-10 .dbn files to front-month ZC parquet.")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help=f"Directory containing .dbn files (default: {RAW_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output parquet path (default: {OUTPUT_PARQUET})",
    )
    parser.add_argument(
        "--days-csv",
        type=Path,
        default=None,
        help=f"Processed-days tracking CSV (default: {DAYS_PROCESSED_CSV})",
    )
    args = parser.parse_args()
    run(
        raw_dir=args.raw_dir,
        output_parquet=args.output,
        days_processed_csv=args.days_csv,
    )


if __name__ == "__main__":
    main()
