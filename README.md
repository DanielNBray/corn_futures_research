# Corn Futures Research

Quantitative analysis of CBOT corn futures using Databento market data.

## Goals
1. Data pipeline: continuous front month series from 2 years of market data
2. Price visualization, OHLCV charting, volume analysis
3. Technical indicators implemented from scratch (SMA, EMA, VWAP, Bollinger Bands)
4. Stochastic analysis (return distributions, drift, volatility, GBM, Monte Carlo, GARCH, Ornstein-Uhlenbeck)
5. Risk analytics (VaR, CVaR, Sharpe, maximum drawdown)

## Setup

### 1. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the data pipeline
```bash
# process MBP-10 data (trades + 3 levels of bid/ask — primary dataset)
python scripts/process_all_data.py --data-dir data/raw/mbp10 --output data/processed/front_month_MBP10.parquet
```

## Data
- **Raw:** `.dbn` files from Databento, split by day, stored in `data/raw/mbp10/`
- **Processed:** Front-month continuous series as parquet in `data/processed/`
- MBO data (order-level) also available in `data/raw/mbo/` for future order book reconstruction work

## Project Structure
```
├── data/raw/MBO_20240205-20260205/             Raw MBO .dbn files (gitignored)
├── data/raw/MBO10_20250216-20260216/           Raw MBP-10 .dbn files (gitignored)
├── data/processed/                             Parquet outputs (gitignored)
├── docs/                                       Methodology, results, project docs
├── notebooks/                                  Jupyter notebooks (one per analysis stage, 7 total)
├── outputs/                                    Charts and reports related to the research 
├── src/                                        Reusable Python package
│   ├── microstructure/                         Process data and calculate features such as OFI, depth imbalance, LOB slope
│   ├── model/                                  Analysis and implementation of volatility, regime, and proof-of-concept strategy
│   └── utils/                                  Plotting and helper stuff
└── requirements.txt
```
