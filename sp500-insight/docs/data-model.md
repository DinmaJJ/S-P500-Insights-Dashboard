# Data Model

## Core Tables

### universe
Current (and optionally historical) S&P 500 constituents.
- symbol (PK-ish), name, sector, sub_industry, date_added, is_active, ...

### prices (Timescale hypertable on `date`)
Daily OHLCV.
- symbol + date unique
- open, high, low, close, adj_close, volume
- source (tiingo / fmp)

### fundamentals
Point-in-time key metrics & ratios.
- symbol + as_of_date unique
- valuation, profitability, growth, health metrics

### company_profiles
Slowly changing descriptive data.
- symbol unique
- description, CEO, employees, website, etc.

### daily_signals
Output of the daily analysis job.
- symbol + signal_date unique
- composite scores (value / quality / momentum / growth)
- overall rank and simple signal (buy / watch / hold / sell)
- key technical snapshots (RSI, SMAs, etc.)

## Future
- `financial_statements` (full income / balance / cashflow if needed)
- `news` / sentiment tables
- `pipeline_runs` for observability
