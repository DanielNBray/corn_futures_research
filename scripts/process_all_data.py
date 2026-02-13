

import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import databento as db
from tqdm import tqdm

"""
builds a continuous front month corn futures series from raw databento .dbn files.
"""

# logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CORN_MONTHS = {
    'H': 3,   # mar
    'K': 5,   # May
    'N': 7,   # Jul
    'U': 9,   # Sep
    'Z': 12,  # dec
}

def generate_front_month_schedule(start_year: int, end_year: int) -> list[list[str]]:
    """generate [expiration_date, symbol] pairs for corn contracts across a year range."""
    schedule = []
    
    for year in range(start_year, end_year + 1):
        year_digit = str(year)[-1]
        
        for month_letter, month_num in CORN_MONTHS.items():
            ''' 
            Using the 14 below because it is the last trading day before the 15th of the contract month. 
            So this is when the futures contract expires.
            '''
            expiration = datetime(year, month_num, 14)   
            while expiration.weekday() >= 5: #counting down until we find a valid trading day to represent the expiration date.
                expiration -= timedelta(days=1)
            
            schedule.append([expiration.strftime('%Y%m%d'), f'ZC{month_letter}{year_digit}']) #E.G. [20260314, ZCH26]
    
    return schedule


def get_year_range_from_files(data_dir: Path) -> tuple[int, int]:
    """parse min/max year from dbn filenames (glbx-mdp3-YYYYMMDD.mbo.dbn)."""
    dbn_files = sorted(data_dir.glob('*.dbn'))
    
    if not dbn_files:
        raise FileNotFoundError(f"no .dbn files found in {data_dir}")
    
    years = [int(f.stem.split('-')[2].split('.')[0][:4]) for f in dbn_files]
    return min(years), max(years)


# generated dynamically in build_continuous_series()
FRONT_MONTH_SCHEDULE = []

FEATURE_COLS = [
    'ts_event', 'price', 'size', 'side',                  # execution
    'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00',   # book level 0
    'bid_px_01', 'ask_px_01', 'bid_sz_01', 'ask_sz_01',   # book level 1
    'bid_px_02', 'ask_px_02', 'bid_sz_02', 'ask_sz_02',   # book level 2
    'symbol'
]


def get_front_month(date_str: str) -> str | None:
    """return the front month contract symbol for a given date."""
    trade_date = datetime.strptime(date_str, '%Y%m%d')
    
    for exp_date, contract in FRONT_MONTH_SCHEDULE:
        expiration = datetime.strptime(exp_date, '%Y%m%d')
        if trade_date <= expiration:
            return contract
    
    logger.warning(f"no front month found for {date_str} - outside schedule range")
    return None


def process_dbn_file(file_path: Path) -> pd.DataFrame | None:
    """extract front month trades from a single dbn file."""
    try:
        date_str = file_path.stem.split('-')[2].split('.')[0]
        front_contract = get_front_month(date_str)
        
        if front_contract is None:
            return None
        
        store = db.DBNStore.from_file(str(file_path))
        df = store.to_df()
        
        trades = df[(df['action'] == 'T') & (df['symbol'] == front_contract)].copy()
        
        if trades.empty:
            logger.debug(f"{date_str}: no {front_contract} trades found")
            return None
        
        available_cols = [col for col in FEATURE_COLS if col in trades.columns]
        trades = trades[available_cols]
        trades['date'] = date_str
        
        logger.info(f"{date_str}: extracted {len(trades)} {front_contract} trades")
        return trades
        
    except Exception as e:
        logger.error(f"failed to process {file_path.name}: {e}")
        return None


def build_continuous_series(data_dir: Path, output_path: Path) -> None:
    """process all dbn files into a single continuous front month parquet."""
    global FRONT_MONTH_SCHEDULE
    
    dbn_files = sorted(data_dir.glob('*.dbn'))
    logger.info(f"found {len(dbn_files)} dbn files to process")
    
    if not dbn_files:
        logger.error(f"no .dbn files found in {data_dir}")
        return
    
    start_year, end_year = get_year_range_from_files(data_dir)
    
    # end_year + 1 because late-december data needs the next year's contracts.
    # e.g. dec 20 2026 data -> front month is ZCH7 (march 2027), which
    # wouldn't exist if we only generated up to 2026.
    FRONT_MONTH_SCHEDULE = generate_front_month_schedule(start_year, end_year + 1)
    logger.info(f"generated expiration schedule for {start_year}-{end_year + 1}")
    
    trades_list = []
    
    for file_path in tqdm(dbn_files, desc="processing dbn files"):
        result = process_dbn_file(file_path)
        if result is not None:
            trades_list.append(result)
    
    if not trades_list:
        logger.error("no valid trade data extracted")
        return
    
    combined = pd.concat(trades_list, ignore_index=True)
    combined.to_parquet(output_path, index=False)
    
    logger.info(f"saved {len(combined):,} trades to {output_path}")
    logger.info(f"date range: {combined['date'].min()} to {combined['date'].max()}")
    logger.info(f"contracts: {sorted(combined['symbol'].unique())}")


def main():
    parser = argparse.ArgumentParser(
        description="extract continuous front month corn futures trade data"
    )
    parser.add_argument(
        '--data-dir',
        type=Path,
        required=True,
        help='directory containing dbn files'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default='corn_front_month_trades.parquet',
        help='output parquet file path'
    )
    
    args = parser.parse_args()
    
    if not args.data_dir.exists():
        logger.error(f"data directory not found: {args.data_dir}")
        return
    
    build_continuous_series(args.data_dir, args.output)


if __name__ == '__main__':
    main()
