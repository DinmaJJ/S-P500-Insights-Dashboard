# S&P 500 Insight

A production-grade, free-tier portfolio project that automatically extracts, transforms, and loads rich data for the S&P 500, runs daily analysis, and presents actionable insights through a modern dashboard.

**Goal**: Help you understand *why* companies in the S&P 500 are worth investing in (or not) by combining multi-year price history, fundamentals, technical indicators, and daily rankings.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  FMP + Tiingo   │────▶│  Prefect ETL     │────▶│  PostgreSQL +      │
│  (Free APIs)    │     │  (self-hosted)   │     │  TimescaleDB       │
└─────────────────┘     └──────────────────┘     └─────────┬──────────┘
                                                          │
                                                          ▼
                                               ┌────────────────────┐
                                               │  FastAPI Backend   │
                                               └─────────┬──────────┘
                                                         │
                                                         ▼
                                               ┌────────────────────┐
                                               │  Next.js Dashboard │
                                               └────────────────────┘
```

### Stack

| Layer              | Technology                          | Notes |
|--------------------|-------------------------------------|-------|
| Data Sources       | Financial Modeling Prep + Tiingo    | Free tiers, complementary strengths |
| Orchestration      | Prefect (self-hosted)               | Free & unlimited when self-hosted |
| Database           | PostgreSQL 16 + TimescaleDB         | Time-series optimized |
| Backend API        | FastAPI + SQLAlchemy 2.0 + Alembic  | Modern, typed, auto-docs |
| Frontend           | Next.js 15 + Tailwind + shadcn/ui   | Beautiful, fast dashboard |
| Infra              | Docker Compose                      | One-command local setup |

## Project Structure

```
sp500-insight/
├── backend/                 # FastAPI application
├── etl/                     # Prefect flows & tasks
├── frontend/                # Next.js dashboard
├── db/                      # Database init scripts
├── scripts/                 # Utility scripts
├── docs/                    # Architecture & data model docs
├── docker-compose.yml
├── .env.example
└── Makefile
```

## Quick Start (Phase 1)

### 1. Prerequisites
- **Docker Desktop** installed and running (Mac / Windows / Linux)
- Free API keys:
  - [Financial Modeling Prep](https://site.financialmodelingprep.com/developer/docs)
  - [Tiingo](https://www.tiingo.com/account/api/token)

### 2. Add your API keys

```bash
cd sp500-insight
cp .env.example .env
```

Open the `.env` file and paste your keys:

```
FMP_API_KEY=your_actual_fmp_key_here
TIINGO_API_KEY=your_actual_tiingo_key_here
```

### 3. Start the services

```bash
make up
```

Wait 10–15 seconds for the database to become healthy.

### 4. Create tables + load S&P 500 list

```bash
make migrate
make seed-universe
```

You should see something like:
```
Created     : 503
Updated     : 0
Active total: 503
```

### 5. Check it worked

- FastAPI docs: http://localhost:8000/docs  
  → Try the `/api/v1/universe` endpoint
- Prefect UI: http://localhost:4200

(Frontend dashboard comes in a later phase)

## Free Tier Strategy

We stay comfortably inside free limits by:

- Maintaining a curated S&P 500 universe (~503 tickers)
- Doing **incremental** daily updates (only new bars + changed fundamentals)
- Spreading heavy backfills across multiple days
- Aggressive caching and upserts
- Computing technical indicators ourselves (no paid indicator endpoints needed)

## Development Phases

1. **Foundation** ✅ — Project scaffold, Docker, DB models, Alembic, universe seeder
2. **Data Pipeline** (next) — Extract prices + fundamentals, transform, load
3. **Analysis Engine** — Technical indicators, fundamental scores, rankings
4. **API Layer** — Richer FastAPI endpoints
5. **Dashboard** — Interactive Next.js frontend with charts and signals
6. **Polish** — Tests, CI, better observability, documentation

## License

MIT — built as a learning / portfolio project.
