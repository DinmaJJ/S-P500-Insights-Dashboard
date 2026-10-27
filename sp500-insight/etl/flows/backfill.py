"""
Historical backfill flow.

Because free tiers are rate-limited, backfills should be run carefully
(e.g. a few dozen symbols per day or with heavy delays).
"""

from prefect import flow, task
import structlog

logger = structlog.get_logger()


@task
def backfill_prices(symbols: list[str], start_date: str = "2015-01-01"):
    logger.info("Backfilling prices (placeholder)", symbols=len(symbols), start=start_date)
    return {"status": "todo"}


@flow(name="sp500-backfill")
def backfill(symbols: list[str] | None = None):
    if symbols is None:
        # In real version we pull active universe from DB
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]  # example

    result = backfill_prices(symbols)
    return result


if __name__ == "__main__":
    backfill()
