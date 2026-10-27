# Architecture

## Goals
- Fully automated daily pipeline using free APIs
- Rich feature set for understanding and ranking S&P 500 stocks
- Clean separation of concerns (ETL / API / Frontend)
- Production-grade practices (Docker, migrations, observability, typed code)

## Data Flow
1. **Extract** – FMP (fundamentals, profiles, universe) + Tiingo (clean long-history OHLCV)
2. **Transform** – Cleaning, validation, feature engineering (technical indicators, scores)
3. **Load** – Upserts into PostgreSQL / TimescaleDB
4. **Analyze** – Daily rankings and signals written to `daily_signals`
5. **Serve** – FastAPI exposes data; Next.js dashboard consumes it

## Free Tier Discipline
- Curated universe of ~503 symbols
- Incremental updates only
- Backfills throttled and spread over time
- Heavy use of upserts and caching

## Key Design Decisions
- TimescaleDB hypertables for prices and signals
- Prefect for orchestration (self-hosted for unlimited free usage)
- FastAPI for a clean, documented API surface
- Next.js App Router + Tailwind for a modern dashboard
