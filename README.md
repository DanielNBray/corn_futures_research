# Corn Futures Research

Quantitative analysis of CBOT corn futures using Databento market data.

## Goals
1. Data pipeline: continuous front month series from 2 years of MBO data
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
python scripts/process_all_data.py --data-dir data/raw --output data/processed/front_month_trades.parquet
```

### 4. Open notebooks
```bash
jupyter notebook
```

## Project Structure
```
├── data/raw/              Raw .dbn files (gitignored)
├── data/processed/        Parquet outputs (gitignored)
├── docs/                  Methodology, results, project docs
├── notebooks/             Jupyter notebooks (one per analysis stage)
├── scripts/               Command-line data processing scripts
├── src/                   Reusable Python package
│   ├── analysis/          Stochastic metrics, visualization helpers
│   ├── corn_research/     Data processing, contract calendar
│   └── features/          Technical indicator calculations
├── tests/                 Automated tests
└── requirements.txt
```
