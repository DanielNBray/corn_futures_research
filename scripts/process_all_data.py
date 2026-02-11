"""
Front month corn futures trade data extraction with order book snapshots.

Processes Databento MBO data to construct continuous front month series,
preserving top-3 order book levels at trade execution for ML feature engineering.
"""

import argparse
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import databento as db
from tqdm import tqdm

# configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# corn futures expiration schedule (business day before 15th of month)
FRONT_MONTH_SCHEDULE = [ #YYYYMMDD , Symbol ]
    ['20240314', 'ZCH4'], ['20240514', 'ZCK4'], ['20240712', 'ZCN4'], 
    ['20240913', 'ZCU4'], ['20241213', 'ZCZ4'], ['20250314', 'ZCH5'], 
    ['20250514', 'ZCK5'], ['20250714', 'ZCN5'], ['20250912', 'ZCU5'], 
    ['20251212', 'ZCZ5'], ['20260313', 'ZCH6']
]

# columns to preserve for ml and analysis
FEATURE_COLS = [
    'ts_event', 'price', 'size', 'side',  # execution
    'bid_px_00', 'ask_px_00', 'bid_sz_00', 'ask_sz_00',  # level 0
    'bid_px_01', 'ask_px_01', 'bid_sz_01', 'ask_sz_01',  # level 1
    'bid_px_02', 'ask_px_02', 'bid_sz_02', 'ask_sz_02',  # level 2
    'symbol'
]


def get_front_month(date_str: str) -> str | None:
    """determine front month contract for given date based on expiration schedule"""
    trade_date = datetime.strptime(date_str, '%Y%m%d')
    
    for exp_date, contract in FRONT_MONTH_SCHEDULE:
        expiration = datetime.strptime(exp_date, '%Y%m%d')
        if trade_date <= expiration:
            return contract
    
    logger.warning(f"no front month found for {date_str} - outside schedule range")
    return None


def process_dbn_file(file_path: Path) -> pd.DataFrame | None:
    """extract front month trades with order book snapshots from single dbn file"""
    try:
        # parse date from filename (glbx-mdp3-YYYYMMDD.mbo.dbn)
        date_str = file_path.stem.split('-')[2].split('.')[0]
        front_contract = get_front_month(date_str)
        
        if front_contract is None:
            return None
        
        # load and filter data
        store = db.DBNStore.from_file(str(file_path))
        df = store.to_df()
        
        # keep only trade events for front month
        trades = df[(df['action'] == 'T') & (df['symbol'] == front_contract)].copy()
        
        if trades.empty:
            logger.debug(f"{date_str}: no {front_contract} trades found")
            return None
        
        # select relevant columns (gracefully handle missing columns)
        available_cols = [col for col in FEATURE_COLS if col in trades.columns]
        trades = trades[available_cols]
        trades['date'] = date_str
        
        logger.info(f"{date_str}: extracted {len(trades)} {front_contract} trades")
        return trades
        
    except Exception as e:
        logger.error(f"failed to process {file_path.name}: {e}")
        return None


def build_continuous_series(data_dir: Path, output_path: Path) -> None:
    """construct continuous front month series from directory of dbn files"""
    dbn_files = sorted(data_dir.glob('*.dbn'))
    logger.info(f"found {len(dbn_files)} dbn files to process")
    
    if not dbn_files:
        logger.error(f"no .dbn files found in {data_dir}")
        return
    
    trades_list = []
    
    for file_path in tqdm(dbn_files, desc="processing dbn files"):
        result = process_dbn_file(file_path)
        if result is not None:
            trades_list.append(result)
    
    if not trades_list:
        logger.error("no valid trade data extracted")
        return
    
    # combine and save
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
