"""
builds continuous front month corn futures datasets from raw databento .dbn files.

supports two output modes:
  - "trades"          -> just trade events (price, size, side)
  - "trades_with_book" -> trade events + 3 levels of bid/ask book snapshots

the raw MBO data can be converted to other schemas on the fly via databento's
store.to_df(schema=...) — no need to re-download data.
"""

import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import databento as db
from tqdm import tqdm

# logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CORN_MONTHS = {
    'H': 3,   # mar
    'K': 5,   # may
    'N': 7,   # jul
    'U': 9,   # sep
    'Z': 12,  # dec
}

# output mode configs: schema to pass to databento, columns to keep, default filename
OUTPUT_MODES = {
    'trades': {
        'schema': None,            # raw MBO, filter to action == 'T'
        'columns': ['ts_event', 'price', 'size', 'side', 'symbol'],
        'default_output': 'data/processed/front_month_trades.parquet',
    },
    'trades_with_book': {
        'schema': 'mbp-10',       # converts MBO -> 10-level book, we keep 3
        'columns': [
            'ts_event', 'price', 'size', 'side',                  # execution
            'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00',   # book level 0
            'bid_px_01', 'ask_px_01', 'bid_sz_01', 'ask_sz_01',   # book level 1
            'bid_px_02', 'ask_px_02', 'bid_sz_02', 'ask_sz_02',   # book level 2
            'symbol',
        ],
        'default_output': 'data/processed/front_month_trades_book.parquet',
    },
}

# generated dynamically in build_continuous_series()
FRONT_MONTH_SCHEDULE = []


def generate_front_month_schedule(start_year: int, end_year: int) -> list[list[str]]:
    """generate [expiration_date, symbol] pairs for corn contracts across a year range."""
    schedule = []

    for year in range(start_year, end_year + 1):
        year_digit = str(year)[-1]

        for month_letter, month_num in CORN_MONTHS.items():
            # last trading day = business day before the 15th
            expiration = datetime(year, month_num, 14)
            while expiration.weekday() >= 5:
                expiration -= timedelta(days=1)

            schedule.append([expiration.strftime('%Y%m%d'), f'ZC{month_letter}{year_digit}'])

    return schedule


def get_year_range_from_files(data_dir: Path) -> tuple[int, int]:
    """parse min/max year from dbn filenames (glbx-mdp3-YYYYMMDD.mbo.dbn)."""
    dbn_files = sorted(data_dir.glob('*.dbn'))

    if not dbn_files:
        raise FileNotFoundError(f"no .dbn files found in {data_dir}")

    years = [int(f.stem.split('-')[2].split('.')[0][:4]) for f in dbn_files]
    return min(years), max(years)


def get_front_month(date_str: str) -> str | None:
    """return the front month contract symbol for a given date."""
    trade_date = datetime.strptime(date_str, '%Y%m%d')

    for exp_date, contract in FRONT_MONTH_SCHEDULE:
        expiration = datetime.strptime(exp_date, '%Y%m%d')
        if trade_date <= expiration:
            return contract

    logger.warning(f"no front month found for {date_str} - outside schedule range")
    return None


def process_dbn_file(file_path: Path, mode_config: dict) -> pd.DataFrame | None:
    """extract front month trades from a single dbn file using the given mode config."""
    try:
        date_str = file_path.stem.split('-')[2].split('.')[0]
        front_contract = get_front_month(date_str)

        if front_contract is None:
            return None

        store = db.DBNStore.from_file(str(file_path))

        # convert schema if needed (e.g. MBO -> MBP-10 for book data)
        schema = mode_config['schema']
        if schema:
            df = store.to_df(schema=schema)
        else:
            df = store.to_df()

        trades = df[(df['action'] == 'T') & (df['symbol'] == front_contract)].copy()

        if trades.empty:
            logger.debug(f"{date_str}: no {front_contract} trades found")
            return None

        # keep only columns that exist in this schema
        available_cols = [col for col in mode_config['columns'] if col in trades.columns]
        trades = trades[available_cols]
        trades['date'] = date_str

        logger.info(f"{date_str}: extracted {len(trades)} {front_contract} trades")
        return trades

    except Exception as e:
        logger.error(f"failed to process {file_path.name}: {e}")
        return None


def build_continuous_series(data_dir: Path, output_path: Path, mode: str) -> None:
    """process new dbn files and append to existing parquet (skips already-processed dates)."""
    global FRONT_MONTH_SCHEDULE

    mode_config = OUTPUT_MODES[mode]

    dbn_files = sorted(data_dir.glob('*.dbn'))
    logger.info(f"found {len(dbn_files)} dbn files in {data_dir}")
    logger.info(f"output mode: {mode}")

    if not dbn_files:
        logger.error(f"no .dbn files found in {data_dir}")
        return

    start_year, end_year = get_year_range_from_files(data_dir)

    # end_year + 1 because late-december data needs the next year's contracts.
    # e.g. dec 20 2026 data -> front month is ZCH7 (march 2027), which
    # wouldn't exist if we only generated up to 2026.
    FRONT_MONTH_SCHEDULE = generate_front_month_schedule(start_year, end_year + 1)
    logger.info(f"generated expiration schedule for {start_year}-{end_year + 1}")

    # if output already exists, load it and figure out which dates are already processed
    existing_df = None
    existing_dates = set()
    if output_path.exists():
        existing_df = pd.read_parquet(output_path)
        existing_dates = set(existing_df['date'].unique())
        logger.info(f"existing parquet has {len(existing_dates)} dates already processed")

    # filter to only new files
    new_files = []
    for f in dbn_files:
        date_str = f.stem.split('-')[2].split('.')[0]
        if date_str not in existing_dates:
            new_files.append(f)

    if not new_files:
        logger.info("no new data to process — all dates already in output")
        return

    logger.info(f"processing {len(new_files)} new files (skipping {len(dbn_files) - len(new_files)} already processed)")

    trades_list = []
    for file_path in tqdm(new_files, desc=f"processing ({mode})"):
        result = process_dbn_file(file_path, mode_config)
        if result is not None:
            trades_list.append(result)

    if not trades_list:
        logger.error("no valid trade data extracted from new files")
        return

    new_data = pd.concat(trades_list, ignore_index=True)

    # append to existing data or create fresh
    if existing_df is not None:
        combined = pd.concat([existing_df, new_data], ignore_index=True)
    else:
        combined = new_data

    # sort by date and timestamp for clean output
    combined = combined.sort_values(['date', 'ts_event']).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(output_path, index=False)

    logger.info(f"saved {len(combined):,} total trades to {output_path}")
    logger.info(f"  new: {len(new_data):,} trades from {len(new_files)} files")
    logger.info(f"  date range: {combined['date'].min()} to {combined['date'].max()}")
    logger.info(f"  contracts: {sorted(combined['symbol'].unique())}")


def main():
    parser = argparse.ArgumentParser(
        description="build continuous front month corn futures datasets"
    )
    parser.add_argument(
        '--data-dir',
        type=Path,
        required=True,
        help='directory containing dbn files'
    )
    parser.add_argument(
        '--mode',
        choices=list(OUTPUT_MODES.keys()),
        default='trades',
        help='output mode: "trades" (price/size/side only) or "trades_with_book" (+ 3 levels of bid/ask)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='output parquet path (defaults based on mode)'
    )

    args = parser.parse_args()

    if not args.data_dir.exists():
        logger.error(f"data directory not found: {args.data_dir}")
        return

    # use mode-specific default output if not provided
    output_path = args.output or Path(OUTPUT_MODES[args.mode]['default_output'])

    build_continuous_series(args.data_dir, output_path, args.mode)


if __name__ == '__main__':
    main()


'''
usage:

# trades only (lightweight, for OHLCV / charts / returns / risk)
python scripts/process_all_data.py --data-dir data/raw --mode trades

# trades + 3 levels of bid/ask (for microstructure / spread analysis)
python scripts/process_all_data.py --data-dir data/raw --mode trades_with_book

# both at once
python scripts/process_all_data.py --data-dir data/raw --mode trades && python scripts/process_all_data.py --data-dir data/raw --mode trades_with_book
'''

