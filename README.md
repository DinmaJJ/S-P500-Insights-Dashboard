# S&P 500 Insight

**A stock-market data engineering platform for collecting, storing, and
exploring S&P 500 market data.**

S&P 500 Insight is a project that brings together market-data ingestion,
time-series storage, a backend API, and an interactive dashboard. Its
longer-term goal is to support transparent stock analysis using value,
quality, and momentum factors.

**Live demo:** https://s-p500-insights-dashboard.streamlit.app/\
**Repository:** https://github.com/DinmaJJ/S-P500-Insights-Dashboard

> **Project status:** In development. The current data pipeline and
> database foundation support a limited dataset of 25 stocks, while the
> universe table contains 503 constituents. Based on the current project
> notes, the scoring engine, populated daily signals, complete API
> workflow, and Next.js frontend remain planned work. Update this status
> as implementation changes.

## Table of contents

-   [Project overview](#project-overview)
-   [Current status](#current-status)
-   [Architecture](#architecture)
-   [Technology stack](#technology-stack)
-   [Data model](#data-model)
-   [Data ingestion workflow](#data-ingestion-workflow)
-   [Design decisions](#design-decisions)
-   [Technical challenges](#technical-challenges)
-   [Getting started](#getting-started)
-   [Roadmap](#roadmap)
-   [Limitations](#limitations)
-   [Disclaimer](#disclaimer)

## Project overview

Financial analysis often requires data from multiple sources, including
historical prices, company fundamentals, and a current list of index
constituents. Before this data can support useful comparisons, it must
be collected, normalized, stored, and updated consistently.

S&P 500 Insight is being developed to provide that foundation. Python
scripts collect and update market data; PostgreSQL stores structured
records; TimescaleDB supports time-series price data; Alembic tracks
database schema changes; FastAPI is the planned interface for accessing
backend data; and Streamlit provides a live dashboard for exploring the
project.

The intended analytical direction is to compare stocks using three
factors:

-   **Value:** valuation measures such as price-to-earnings (P/E) and
    price-to-book (P/B), where data is available and appropriate.
-   **Quality:** profitability and balance-sheet measures such as return
    on equity (ROE), margins, and debt-related ratios.
-   **Momentum:** recent returns and price trends, potentially including
    price relative to a 200-day moving average.

The future scoring layer is intended to combine defined metrics into a
ranking and interpretable signals. These signals are not described as
implemented until the scoring logic is complete and its results are
being written and served.

## Current status

Based on the current development notes:

  -----------------------------------------------------------------------
  Component                           Status
  ----------------------------------- -----------------------------------
  S&P 500 universe seeding from       Implemented; last recorded result
  Wikipedia                           was 503 active constituents

  Price backfill from Tiingo          Implemented for a limited set of 25
                                      stocks

  Fundamentals and company profiles   Implemented for a limited set of 25
  from yfinance                       stocks, subject to provider field
                                      availability

  PostgreSQL and TimescaleDB schema   Implemented

  Alembic database migrations         Implemented

  Upsert-based data updates           Implemented in ingestion workflows

  Docker Compose development          Implemented
  environment                         

  Streamlit dashboard                 Deployed; see live demo

  Value, quality, and momentum        Planned / not yet built according
  scoring engine                      to current notes

  Populated `daily_signals` outputs   Not yet available according to
                                      current notes

  Complete FastAPI endpoints for      Remaining work; verify the
  prices, fundamentals, and rankings  currently available routes

  Prefect scheduling for daily        Planned
  ingestion                           

  Next.js frontend                    Not built; placeholder only

  Full-universe historical backfill   Planned
  -----------------------------------------------------------------------

The recorded dataset snapshot was approximately 31,350 daily price rows
(25 stocks × roughly 1,254 trading days), 25 latest fundamental
snapshots, and 25 company profiles. These counts are a development
snapshot, not a guarantee of the current live database state.

## Architecture

The intended high-level data flow is:

``` text
External sources
  ├── Tiingo: historical price data
  ├── yfinance: fundamentals and company profiles
  └── Wikipedia: S&P 500 constituent universe
                 |
                 v
         Python ETL scripts
       fetch, normalize, upsert
                 |
                 v
     PostgreSQL 16 + TimescaleDB
       universe, prices, fundamentals,
       company_profiles, daily_signals
                 |
                 v
             FastAPI
      planned data-access interface
                 |
                 v
      Applications and consumers
      Streamlit demo / future clients
```

Docker Compose runs the development services in a shared private
network. The current orchestration is primarily script-driven; Prefect
is planned for scheduled workflows.

The architecture diagram represents the intended system. Confirm the
live dashboard's exact data connection and the currently implemented API
routes before describing them as active integrations.

## Technology stack

  -----------------------------------------------------------------------
  Technology                          Purpose
  ----------------------------------- -----------------------------------
  Python                              Ingestion scripts, data processing,
                                      and application logic

  Tiingo                              Historical and daily market-price
                                      data

  yfinance                            Company profiles and available
                                      fundamental fields

  Wikipedia                           Initial S&P 500 constituent list

  PostgreSQL 16                       Relational storage

  TimescaleDB                         Time-series functionality for price
                                      and signal tables

  SQLAlchemy 2.0                      Python database access and ORM,
                                      where used

  Alembic                             Versioned database schema
                                      migrations

  FastAPI                             Backend API framework

  Docker Compose                      Local service orchestration and
                                      reproducible development
                                      environment

  Streamlit                           Live interactive dashboard

  Prefect                             Planned orchestration for scheduled
                                      data workflows

  Next.js                             Possible future frontend; not yet
                                      built
  -----------------------------------------------------------------------

## Data model

The database is organized around the following tables.

  --------------------------------------------------------------------------
  Table                   Purpose                 Key design
  ----------------------- ----------------------- --------------------------
  `universe`              Master list of S&P 500  Unique stock symbol and an
                          constituents            `is_active` flag

  `prices`                Daily OHLCV             Composite key on
                          observations            `(symbol, date)`;
                                                  configured as a hypertable

  `fundamentals`          Dated company financial Unique key on
                          metrics                 `(symbol, as_of_date)`

  `company_profiles`      Company metadata such   Unique stock symbol
                          as sector and industry  

  `daily_signals`         Intended storage for    Composite key on
                          factor scores, overall  `(symbol, signal_date)`;
                          scores, ranks, and      intended as a hypertable
                          signals                 
  --------------------------------------------------------------------------

### Why PostgreSQL and TimescaleDB?

PostgreSQL provides relational tables, constraints, SQL querying, and
transaction support. TimescaleDB extends PostgreSQL with features for
time-series workloads, which are relevant to dated stock-price
observations.

A hypertable is TimescaleDB's time-partitioned abstraction for
time-series data. The time column must be part of every unique index,
including the primary key, on a hypertable. This is why the price and
signal tables use composite keys that include their time column.

A hypertable does not automatically guarantee that every query will be
faster. Performance depends on schema design, indexes, query patterns,
and data volume.

## Data ingestion workflow

### 1. Seed the constituent universe

A Python script parses the Wikipedia S&P 500 constituents page. The
parser uses standard HTML parsing rather than requiring BeautifulSoup.

The script uses upsert-style logic to add new symbols and update
existing constituent metadata. Symbols no longer present in the latest
source are marked inactive rather than simply disappearing from the
master table.

The latest recorded seed operation returned 503 active constituents. The
live index list can change over time.

### 2. Backfill historical prices

The `backfill_small.py` workflow currently targets a limited group of 25
major stocks to keep early development manageable and reduce pressure on
provider limits.

Price data is fetched from Tiingo, with approximately five years of
adjusted daily OHLCV in the recorded setup. The ingestion code uses
PostgreSQL `INSERT ... ON CONFLICT ... DO UPDATE` behavior with
`(symbol, date)` as the conflict key.

Ticker-symbol conventions can differ between sources. For example, a
provider may represent a class-share ticker with a hyphen while another
uses a dot. Symbol normalization is therefore an important integration
concern.

### 3. Load fundamentals and company profiles

The project uses yfinance for available company profile and fundamental
data after encountering repeated HTTP 403 errors with the Financial
Modeling Prep free tier.

Fields may include market capitalization, valuation multiples,
profitability measures, debt ratios, sector, industry, and company
description, depending on availability. These fields should not be
assumed to exist for every company or to share identical definitions
across sources.

### 4. Make ingestion repeatable

Upserts allow records to be inserted when new and updated when they
already exist. This supports **idempotent ingestion**: rerunning a
workflow with the same source data should not create duplicate
observations.

True idempotency still depends on stable keys, consistent normalization,
and correctly implemented conflict handling.

### 5. Store data for downstream use

The database holds the constituent universe, historical prices,
fundamentals, company profiles, and the intended destination for daily
analytical signals. The next major analytical step is to calculate
factor features and persist their outputs to `daily_signals`.

## Design decisions

### Versioned schema with Alembic

Alembic migrations make database structure changes explicit and
repeatable. The initial migration creates the core tables and configures
the price and signal tables as hypertables.

During development, a migration-version conflict occurred because
Prefect used the same database as the application and wrote its own
`alembic_version` table. The services were separated into distinct
databases: the application database and a dedicated `prefect` database.
This avoids treating two independently managed schemas as if they shared
one migration history.

### Docker Compose for local services

Docker Compose defines the development services and their network.
Containers can reach each other using Compose service names, for example
`db:5432` for the database from another service on the same network. A
developer's browser normally reaches published local ports such as the
API on port 8000 or the Prefect UI on port 4200, when those services are
running and mapped accordingly.

The database uses a named volume so data can persist across container
restarts. Health checks help coordinate service startup, although
applications should still handle connection failures gracefully.

### Separation of responsibilities

The project separates data ingestion, database schema management,
backend access, infrastructure, and presentation. This makes each
concern easier to change and test independently.

## Technical challenges

  -----------------------------------------------------------------------
  Challenge               Cause                   Resolution recorded
                                                  during development
  ----------------------- ----------------------- -----------------------
  Alembic could not       Prefect and the         Created a separate
  locate a revision       application shared a    database for Prefect
                          database and            
                          migration-version table 

  TimescaleDB rejected a  The primary key did not Used composite keys
  hypertable key          include the             including the time
                          partitioning time       column
                          column                  

  Financial Modeling Prep Free-tier access        Switched the
  returned HTTP 403       restrictions or         fundamentals/profile
                          endpoint limitations    workflow to yfinance

  Command-line utilities  Restricted or missing   Used Docker Compose
  were unavailable in the host tools              commands and tools
  local environment                               inside containers

  Source values exceeded  Incoming Wikipedia text Expanded relevant
  database column lengths was wider than the      columns and cleaned
                          original schema allowed parser output
  -----------------------------------------------------------------------

These examples show practical debugging across database design, provider
integration, containerized development, and source-data handling.

## Getting started

The commands below are a template based on the development setup. Verify
filenames, service names, environment variables, and application entry
points against the current repository before relying on them.

### Prerequisites

-   Git
-   Docker Desktop or Docker Engine with Docker Compose
-   API credentials required by the data providers
-   Python, if running scripts outside containers

### 1. Clone the repository

``` bash
git clone https://github.com/DinmaJJ/S-P500-Insights-Dashboard.git
cd S-P500-Insights-Dashboard/sp500-insight
```

### 2. Configure secrets

If the repository contains an `.env.example`, copy it to `.env` and set
the required values:

``` bash
cp .env.example .env
```

Use the exact variable names expected by the application. Never commit
`.env` files, API keys, passwords, or credential-bearing database URLs.

### 3. Start the services

From the directory containing the relevant Compose file:

``` bash
docker compose up --build
```

If the Compose file is in a different directory or there are multiple
Compose configurations, use the project's actual documented path.

### 4. Apply migrations

If Alembic is configured in the environment where you are running the
command:

``` bash
alembic upgrade head
```

Follow the project's migration instructions if migrations run
automatically in the container or require a specific working directory.

### 5. Run ingestion

Run the universe seeding or limited backfill script using the entry
points and environment configured in the repository. Check provider rate
limits before expanding the number of symbols.

### 6. Explore the demo

Open the deployed dashboard:

https://s-p500-insights-dashboard.streamlit.app/

The exact local API and dashboard commands depend on the Compose
configuration and application entry points.

## Roadmap

1.  Expand price and fundamentals coverage beyond the initial 25 stocks
    with rate-limit-aware ingestion.
2.  Add incremental daily updates so routine runs fetch only new or
    changed observations where possible.
3.  Implement and test technical indicators such as moving averages,
    RSI, and multi-window returns.
4.  Implement fundamental metrics and define transparent missing-data
    and normalization rules.
5.  Combine value, quality, and momentum into documented factor scores
    and an overall ranking.
6.  Write dated scoring results to `daily_signals`.
7.  Complete and document FastAPI endpoints for prices, fundamentals,
    stock details, and rankings.
8.  Add Prefect orchestration for scheduled and observable workflows.
9.  Build the planned Next.js frontend if it remains a project goal.
10. Add tests, monitoring, data-freshness checks, and historical
    evaluation of the scoring methodology.

## Limitations and data considerations

-   Provider fields, API limits, access policies, and licensing may
    change.
-   The currently recorded backfill covers only a subset of the S&P 500,
    not the entire universe.
-   A current constituents list is not a historically accurate
    membership list for every past date. Historical evaluations should
    account for constituent changes to reduce survivorship bias.
-   Financial data can be missing, delayed, revised, or defined
    differently by different sources.
-   Adjusted and unadjusted prices have different uses and must be
    selected consistently for each calculation.
-   A scoring system should document metric definitions, normalization,
    weighting, data timestamps, and missing-data rules.
-   Signals such as buy, watch, hold, or avoid are planned analytical
    outputs until the scoring engine is implemented and validated.

## Disclaimer

This project is for educational and technical demonstration purposes
only. It is not financial advice and does not guarantee investment
performance. Any future ranking or signal should be interpreted in the
context of its methodology, data quality, limitations, and independent
research.

## Author

**DinmaJJ**\
GitHub: [@DinmaJJ](https://github.com/DinmaJJ)

------------------------------------------------------------------------

*Keep this README synchronized with the code. Update the current-status
table whenever a planned feature is implemented and tested.*
