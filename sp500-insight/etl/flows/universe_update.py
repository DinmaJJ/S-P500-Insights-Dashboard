"""Refresh the S&P 500 universe from FMP (or Wikipedia fallback)."""

from prefect import flow, task
import structlog
from etl.clients.fmp import FMPClient

logger = structlog.get_logger()


@task
def fetch_sp500_list() -> list[dict]:
    client = FMPClient()
    try:
        data = client.get_sp500_constituents()
        logger.info("Fetched S&P 500 constituents", count=len(data))
        return data
    finally:
        client.close()


@task
def upsert_universe(constituents: list[dict]):
    """Upsert into the universe table (implementation in next phase)."""
    logger.info("Would upsert universe", count=len(constituents))
    # TODO: connect to DB and upsert
    return len(constituents)


@flow(name="sp500-universe-update")
def update_universe():
    constituents = fetch_sp500_list()
    count = upsert_universe(constituents)
    return {"updated": count}


if __name__ == "__main__":
    update_universe()
