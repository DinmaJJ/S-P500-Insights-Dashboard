"""
Seed / refresh the S&P 500 universe.
Primary source: Wikipedia (free & reliable)
Fallback: Financial Modeling Prep (if available)
"""

from __future__ import annotations
import os
import sys
from datetime import datetime, date
from typing import Any

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.config import get_settings
from app.models.universe import Universe


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def fetch_sp500_from_wikipedia() -> list[dict[str, Any]]:
    """Scrape current S&P 500 list from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    from html.parser import HTMLParser

    class TableParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_table = False
            self.in_row = False
            self.in_cell = False
            self.current_row = []
            self.rows = []
            self.table_count = 0
            self.current_cell = ""

        def handle_starttag(self, tag, attrs):
            if tag == "table":
                self.table_count += 1
                if self.table_count == 1:  # first table is the constituents
                    self.in_table = True
            elif self.in_table and tag == "tr":
                self.in_row = True
                self.current_row = []
            elif self.in_table and self.in_row and tag in ("td", "th"):
                self.in_cell = True
                self.current_cell = ""

        def handle_endtag(self, tag):
            if tag == "table" and self.in_table:
                self.in_table = False
            elif tag == "tr" and self.in_row:
                self.in_row = False
                if self.current_row:
                    self.rows.append(self.current_row)
            elif tag in ("td", "th") and self.in_cell:
                self.in_cell = False
                self.current_row.append(self.current_cell.strip())

        def handle_data(self, data):
            if self.in_cell:
                self.current_cell += data

    parser = TableParser()
    parser.feed(html)

    results = []
    # Skip header row
    for row in parser.rows[1:]:
        if len(row) < 2:
            continue

        symbol = row[0].strip()
        name = row[1].strip() if len(row) > 1 else symbol
        sector = row[2].strip() if len(row) > 2 else None
        sub_industry = row[3].strip() if len(row) > 3 else None
        headquarters = row[4].strip() if len(row) > 4 else None
        date_added = row[5].strip() if len(row) > 5 else None
        cik = row[6].strip() if len(row) > 6 else None
        founded = row[7].strip() if len(row) > 7 else None

        # Clean up messy values
        if cik and len(cik) > 20:
            cik = cik[:20]
        if founded and len(founded) > 40:
            founded = founded[:40]
        if headquarters and len(headquarters) > 250:
            headquarters = headquarters[:250]

        if not symbol or len(symbol) > 10:
            continue

        results.append({
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "subSector": sub_industry,
            "headQuarter": headquarters,
            "dateFirstAdded": date_added,
            "cik": cik,
            "founded": founded,
        })

    if len(results) < 400:
        raise RuntimeError(f"Wikipedia parse returned too few rows: {len(results)}")

    return results


def fetch_sp500_from_fmp(api_key: str) -> list[dict[str, Any]]:
    url = "https://financialmodelingprep.com/api/v3/sp500_constituent"
    params = {"apikey": api_key}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected response from FMP: {data}")
        return data


def upsert_universe(session: Session, constituents: list[dict[str, Any]]) -> dict:
    existing = {
        row.symbol: row
        for row in session.scalars(select(Universe)).all()
    }

    seen_symbols: set[str] = set()
    created = 0
    updated = 0

    for item in constituents:
        symbol = (item.get("symbol") or "").strip().upper()
        if not symbol:
            continue

        seen_symbols.add(symbol)
        name = item.get("name") or symbol
        sector = item.get("sector")
        sub_industry = item.get("subSector") or item.get("sub_industry")
        headquarters = item.get("headQuarter") or item.get("headquarters")
        date_added = parse_date(item.get("dateFirstAdded") or item.get("date_added"))
        cik = item.get("cik")
        founded = item.get("founded")

        if symbol in existing:
            row = existing[symbol]
            row.name = name
            row.sector = sector
            row.sub_industry = sub_industry
            row.headquarters = headquarters
            row.date_added = date_added
            row.cik = cik
            row.founded = founded
            row.is_active = True
            row.updated_at = datetime.utcnow()
            updated += 1
        else:
            row = Universe(
                symbol=symbol,
                name=name,
                sector=sector,
                sub_industry=sub_industry,
                headquarters=headquarters,
                date_added=date_added,
                cik=cik,
                founded=founded,
                is_active=True,
            )
            session.add(row)
            created += 1

    # Mark symbols no longer in the index as inactive
    deactivated = 0
    for symbol, row in existing.items():
        if symbol not in seen_symbols and row.is_active:
            row.is_active = False
            row.updated_at = datetime.utcnow()
            deactivated += 1

    session.commit()
    return {
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
        "total_active": len(seen_symbols),
    }


def main() -> None:
    settings = get_settings()
    db_url = os.getenv("DATABASE_URL_SYNC") or settings.database_url_sync
    print("Connecting to database...")
    engine = create_engine(db_url)

    constituents = None

    # Try Wikipedia first (most reliable free source)
    try:
        print("Fetching S&P 500 constituents from Wikipedia...")
        constituents = fetch_sp500_from_wikipedia()
        print(f"Received {len(constituents)} constituents from Wikipedia")
    except Exception as e:
        print(f"Wikipedia failed: {e}")

    # Fallback to FMP if Wikipedia fails
    if not constituents:
        api_key = settings.fmp_api_key or os.getenv("FMP_API_KEY")
        if api_key:
            try:
                print("Trying Financial Modeling Prep as fallback...")
                constituents = fetch_sp500_from_fmp(api_key)
                print(f"Received {len(constituents)} constituents from FMP")
            except Exception as e:
                print(f"FMP also failed: {e}")

    if not constituents:
        print("ERROR: Could not fetch S&P 500 list from any source.")
        sys.exit(1)

    with Session(engine) as session:
        result = upsert_universe(session, constituents)

    print("Universe seed complete:")
    print(f"  Created     : {result['created']}")
    print(f"  Updated     : {result['updated']}")
    print(f"  Deactivated : {result['deactivated']}")
    print(f"  Active total: {result['total_active']}")


if __name__ == "__main__":
    main()