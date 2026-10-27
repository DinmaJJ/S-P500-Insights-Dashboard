"""
Daily S&P 500 pipeline.

This is a skeleton. We will flesh it out in the next phase:
1. Refresh universe if needed
2. Extract new prices (Tiingo) + any fundamental updates (FMP)
3. Transform & validate
4. Load into Postgres
5. Compute indicators & daily signals
"""

from prefect import flow, task
import structlog

logger = structlog.get_logger()


@task
def extract_prices():
    logger.info("Extracting latest prices (placeholder)")
    return {"status": "todo"}


@task
def extract_fundamentals():
    logger.info("Extracting fundamentals (placeholder)")
    return {"status": "todo"}


@task
def transform(data):
    logger.info("Transforming data (placeholder)")
    return data


@task
def load(data):
    logger.info("Loading data (placeholder)")
    return {"loaded": True}


@task
def analyze():
    logger.info("Running analysis & generating signals (placeholder)")
    return {"signals": []}


@flow(name="sp500-daily-pipeline", log_prints=True)
def daily_pipeline():
    """Main daily orchestration flow."""
    logger.info("Starting daily S&P 500 pipeline")

    prices = extract_prices()
    fundamentals = extract_fundamentals()
    transformed = transform({"prices": prices, "fundamentals": fundamentals})
    load(transformed)
    signals = analyze()

    logger.info("Daily pipeline finished", signals=signals)
    return {"status": "success", "signals": signals}


if __name__ == "__main__":
    daily_pipeline()
