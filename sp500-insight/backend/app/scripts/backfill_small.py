"""
Safe small backfill for Phase 2 testing.
- Prices: Tiingo (~5 years)
- Fundamentals + Profiles: yfinance (free, no API key)
for 25 major S&P 500 stocks.
"""

from __future__ import annotations
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
import yfinance as yf
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.config import get_settings
from app.models.prices import Price
from app.models.fundamentals import Fundamental
from app.models.profiles import CompanyProfile

# --------------------------------------------------
# Config
# --------------------------------------------------
SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "BRK-B", "JPM", "V", "UNH",
    "XOM", "JNJ", "WMT", "MA", "PG",
    "HD", "CVX", "MRK", "ABBV", "KO",
    "PEP", "AVGO", "COST", "LLY", "TMO",
]

START_DATE = (date.today() - timedelta(days=5 * 365)).isoformat()  # ~5 years
SLEEP_BETWEEN_SYMBOLS = 1.0  # seconds


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --------------------------------------------------
# Tiingo client (prices only)
# --------------------------------------------------
class TiingoClient:
    BASE_URL = "https://api.tiingo.com"

    def __init__(self, api_key: str):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {api_key}",
        }
        self.client = httpx.Client(timeout=60.0, headers=self.headers)

    def get_daily_prices(self, symbol: str, start_date: str) -> list[dict]:
        url = f"{self.BASE_URL}/tiingo/daily/{symbol}/prices"
        resp = self.client.get(url, params={"startDate": start_date})
        if resp.status_code == 404 and "-" in symbol:
            alt = symbol.replace("-", ".")
            url = f"{self.BASE_URL}/tiingo/daily/{alt}/prices"
            resp = self.client.get(url, params={"startDate": start_date})
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self.client.close()


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def upsert_prices(session: Session, symbol: str, rows: list[dict]) -> int:
    if not rows:
        return 0

    count = 0
    for row in rows:
        try:
            d = row.get("date") or row.get("Date")
            if not d:
                continue
            if "T" in str(d):
                d = str(d)[:10]
            price_date = datetime.strptime(str(d)[:10], "%Y-%m-%d").date()

            stmt = insert(Price).values(
                symbol=symbol,
                date=price_date,
                open=to_decimal(row.get("open") or row.get("Open")),
                high=to_decimal(row.get("high") or row.get("High")),
                low=to_decimal(row.get("low") or row.get("Low")),
                close=to_decimal(row.get("close") or row.get("Close")),
                adj_close=to_decimal(row.get("adjClose") or row.get("adj_close")),
                volume=row.get("volume") or row.get("Volume"),
                source="tiingo",
                created_at=utcnow(),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "date"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "adj_close": stmt.excluded.adj_close,
                    "volume": stmt.excluded.volume,
                    "source": "tiingo",
                },
            )
            session.execute(stmt)
            count += 1
        except Exception as e:
            print(f"    Warning: could not insert price row for {symbol}: {e}")
            continue

    session.commit()
    return count


def fetch_yfinance_data(symbol: str) -> tuple[dict | None, dict | None]:
    """Return (profile_dict, fundamentals_dict) from yfinance."""
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    if not info or info.get("regularMarketPrice") is None and not info.get("symbol"):
        if "-" in symbol:
            ticker = yf.Ticker(symbol.replace("-", "."))
            info = ticker.info or {}

    if not info:
        return None, None

    profile = {
        "companyName": info.get("longName") or info.get("shortName"),
        "exchange": info.get("exchange"),
        "currency": info.get("currency"),
        "country": info.get("country"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "description": info.get("longBusinessSummary"),
        "ceo": None,
        "fullTimeEmployees": info.get("fullTimeEmployees"),
        "website": info.get("website"),
        "ipoDate": None,
        "image": None,
    }

    fundamentals = {
        "marketCap": info.get("marketCap"),
        "peRatio": info.get("trailingPE") or info.get("forwardPE"),
        "pegRatio": info.get("pegRatio"),
        "pbRatio": info.get("priceToBook"),
        "priceToSalesRatio": info.get("priceToSalesTrailing12Months"),
        "enterpriseValueOverEBITDA": info.get("enterpriseToEbitda"),
        "netProfitMargin": info.get("profitMargins"),
        "operatingProfitMargin": info.get("operatingMargins"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "debtToEquity": info.get("debtToEquity"),
        "currentRatio": info.get("currentRatio"),
        "freeCashFlowPerShare": None,
        "netIncomePerShare": info.get("trailingEps"),
        "dividendYield": info.get("dividendYield"),
    }

    return profile, fundamentals


def upsert_fundamentals(session: Session, symbol: str, metrics: dict) -> int:
    if not metrics:
        return 0

    as_of_date = date.today()

    stmt = insert(Fundamental).values(
        symbol=symbol,
        as_of_date=as_of_date,
        market_cap=to_decimal(metrics.get("marketCap")),
        pe_ratio=to_decimal(metrics.get("peRatio")),
        peg_ratio=to_decimal(metrics.get("pegRatio")),
        price_to_book=to_decimal(metrics.get("pbRatio")),
        price_to_sales=to_decimal(metrics.get("priceToSalesRatio")),
        ev_to_ebitda=to_decimal(metrics.get("enterpriseValueOverEBITDA")),
        profit_margin=to_decimal(metrics.get("netProfitMargin")),
        operating_margin=to_decimal(metrics.get("operatingProfitMargin")),
        return_on_equity=to_decimal(metrics.get("roe")),
        return_on_assets=to_decimal(metrics.get("roa")),
        debt_to_equity=to_decimal(metrics.get("debtToEquity")),
        current_ratio=to_decimal(metrics.get("currentRatio")),
        free_cash_flow=to_decimal(metrics.get("freeCashFlowPerShare")),
        eps=to_decimal(metrics.get("netIncomePerShare")),
        dividend_yield=to_decimal(metrics.get("dividendYield")),
        source="yfinance",
        created_at=utcnow(),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "as_of_date"],
        set_={
            "market_cap": stmt.excluded.market_cap,
            "pe_ratio": stmt.excluded.pe_ratio,
            "peg_ratio": stmt.excluded.peg_ratio,
            "price_to_book": stmt.excluded.price_to_book,
            "price_to_sales": stmt.excluded.price_to_sales,
            "ev_to_ebitda": stmt.excluded.ev_to_ebitda,
            "profit_margin": stmt.excluded.profit_margin,
            "operating_margin": stmt.excluded.operating_margin,
            "return_on_equity": stmt.excluded.return_on_equity,
            "return_on_assets": stmt.excluded.return_on_assets,
            "debt_to_equity": stmt.excluded.debt_to_equity,
            "current_ratio": stmt.excluded.current_ratio,
            "eps": stmt.excluded.eps,
            "dividend_yield": stmt.excluded.dividend_yield,
            "source": "yfinance",
        },
    )
    session.execute(stmt)
    session.commit()
    return 1


def upsert_profile(session: Session, symbol: str, p: dict) -> int:
    if not p:
        return 0

    existing = session.scalar(select(CompanyProfile).where(CompanyProfile.symbol == symbol))
    if existing:
        existing.name = p.get("companyName") or existing.name
        existing.exchange = p.get("exchange")
        existing.currency = p.get("currency")
        existing.country = p.get("country")
        existing.sector = p.get("sector")
        existing.industry = p.get("industry")
        existing.description = p.get("description")
        existing.employees = p.get("fullTimeEmployees")
        existing.website = p.get("website")
        existing.updated_at = utcnow()
    else:
        session.add(CompanyProfile(
            symbol=symbol,
            name=p.get("companyName"),
            exchange=p.get("exchange"),
            currency=p.get("currency"),
            country=p.get("country"),
            sector=p.get("sector"),
            industry=p.get("industry"),
            description=p.get("description"),
            employees=p.get("fullTimeEmployees"),
            website=p.get("website"),
        ))
    session.commit()
    return 1


# --------------------------------------------------
# Main
# --------------------------------------------------
def main() -> None:
    settings = get_settings()
    tiingo_key = settings.tiingo_api_key or os.getenv("TIINGO_API_KEY")

    if not tiingo_key:
        print("ERROR: TIINGO_API_KEY is missing in .env")
        sys.exit(1)

    db_url = os.getenv("DATABASE_URL_SYNC") or settings.database_url_sync
    engine = create_engine(db_url)

    tiingo = TiingoClient(tiingo_key)

    print(f"Starting small backfill for {len(SYMBOLS)} symbols")
    print(f"Price history from: {START_DATE}")
    print("Fundamentals + profiles: yfinance")
    print("-" * 50)

    total_prices = 0
    total_fundamentals = 0
    total_profiles = 0

    try:
        with Session(engine) as session:
            for i, symbol in enumerate(SYMBOLS, 1):
                print(f"[{i}/{len(SYMBOLS)}] {symbol}")

                # --- Prices (Tiingo) ---
                try:
                    rows = tiingo.get_daily_prices(symbol, START_DATE)
                    n = upsert_prices(session, symbol, rows)
                    total_prices += n
                    print(f"    Prices      : {n} rows")
                except Exception as e:
                    print(f"    Prices ERROR: {e}")

                # --- Fundamentals + Profile (yfinance) ---
                try:
                    profile, fundamentals = fetch_yfinance_data(symbol)
                    n_f = upsert_fundamentals(session, symbol, fundamentals or {})
                    n_p = upsert_profile(session, symbol, profile or {})
                    total_fundamentals += n_f
                    total_profiles += n_p
                    print(f"    Fundamentals: {n_f} rows")
                    print(f"    Profile     : {n_p} rows")
                except Exception as e:
                    print(f"    yfinance ERROR: {e}")

                time.sleep(SLEEP_BETWEEN_SYMBOLS)

    finally:
        tiingo.close()

    print("-" * 50)
    print("Backfill complete")
    print(f"  Total price rows     : {total_prices}")
    print(f"  Total fundamentals   : {total_fundamentals}")
    print(f"  Total profiles       : {total_profiles}")


if __name__ == "__main__":
    main()