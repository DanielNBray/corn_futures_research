# Minimum Viable Product

<<<<<<< Current (Your changes)
**Corn Futures Research** — A quantitative analysis project using 2 years of historical MBO corn futures data from Databento.

## Overview

Build a recruiter-ready portfolio piece that demonstrates:

1. **Visualization** — Display the front month contract as a continuous asset: trade prices over time, volume, and related metrics.
2. **Machine Learning** — A Databento-style model that predicts short-term returns from order book features (skew, imbalance), with backtested PnL.
3. **Stochastic Analysis** — Probability distributions of daily returns, correlation, moving averages, drift and volatility, variance estimation, Brownian motion, Monte Carlo simulation, and risk metrics (VaR, drawdown).

## Tech Stack

Python, pandas, matplotlib/plotly, scikit-learn, databento.

## Success

Each phase is implemented, documented, and reproducible. Code is clean and results are interpretable.
=======
## Corn Futures Quantitative Research Platform

A self-contained quantitative research project built on 2 years of MBO (Market-By-Order) corn futures data from CME Globex via Databento. The project progresses through two pillars of quantitative analysis, each building on the last:

### Pillar 1 -- Data Engineering & Visualization
Construct a continuous front month corn futures series from 629 daily `.dbn` files spanning Feb 2024 to Feb 2026. Display the series as professional charts: trade prices over time, volume profiles, OHLCV candlesticks, and contract roll indicators. This demonstrates the ability to build robust data pipelines under real-world memory constraints (40 GB of data on a 16 GB machine).

### Pillar 2 -- Stochastic Analysis, Mathematical Finance & Risk
Apply quantitative finance fundamentals to the corn futures series: estimate return distributions and test their properties against normality; estimate drift and volatility using multiple variance estimators (close-to-close, Parkinson, Garman-Klass); model volatility clustering with GARCH; simulate price paths via Geometric Brownian Motion and Ornstein-Uhlenbeck processes; run Monte Carlo forecasts with confidence intervals; fit heavy-tailed distributions; compute the Hurst exponent; and produce a full risk analytics suite (Value-at-Risk, Conditional VaR, Sharpe ratio, maximum drawdown, coherent risk measure analysis).

### Deliverables
- Processed parquet dataset of continuous front month trades with order book snapshots
- Jupyter notebooks with clear mathematical narrative and visualizations for each analysis stage
- Python package (`src/`) with reusable modules for data processing, technical indicators, stochastic metrics, and visualization
- Written methodology document explaining every decision, formula, derivation, and result
- All code clean enough to serve as a portfolio piece for quant trading recruitment
>>>>>>> Incoming (Background Agent changes)
