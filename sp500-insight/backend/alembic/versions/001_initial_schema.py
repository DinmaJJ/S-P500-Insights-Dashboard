"""Initial schema with TimescaleDB hypertables

Revision ID: 001
Revises:
Create Date: 2026-08-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- universe ---
    op.create_table(
        "universe",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("sub_industry", sa.String(length=150), nullable=True),
        sa.Column("headquarters", sa.String(length=150), nullable=True),
        sa.Column("date_added", sa.Date(), nullable=True),
        sa.Column("cik", sa.String(length=20), nullable=True),
        sa.Column("founded", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index("ix_universe_symbol", "universe", ["symbol"])
    op.create_index("ix_universe_is_active", "universe", ["is_active"])

    # --- prices ---
    # Primary key includes "date" so TimescaleDB can create the hypertable
    op.create_table(
        "prices",
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=True),
        sa.Column("high", sa.Numeric(18, 6), nullable=True),
        sa.Column("low", sa.Numeric(18, 6), nullable=True),
        sa.Column("close", sa.Numeric(18, 6), nullable=True),
        sa.Column("adj_close", sa.Numeric(18, 6), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=True, server_default="tiingo"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("symbol", "date"),
    )
    op.create_index("ix_prices_symbol", "prices", ["symbol"])
    op.create_index("ix_prices_date", "prices", ["date"])

    # Convert prices to TimescaleDB hypertable
    op.execute("SELECT create_hypertable('prices', 'date', if_not_exists => TRUE);")

    # --- fundamentals ---
    op.create_table(
        "fundamentals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("market_cap", sa.Numeric(20, 2), nullable=True),
        sa.Column("pe_ratio", sa.Numeric(12, 4), nullable=True),
        sa.Column("peg_ratio", sa.Numeric(12, 4), nullable=True),
        sa.Column("price_to_book", sa.Numeric(12, 4), nullable=True),
        sa.Column("price_to_sales", sa.Numeric(12, 4), nullable=True),
        sa.Column("ev_to_ebitda", sa.Numeric(12, 4), nullable=True),
        sa.Column("profit_margin", sa.Numeric(12, 6), nullable=True),
        sa.Column("operating_margin", sa.Numeric(12, 6), nullable=True),
        sa.Column("return_on_equity", sa.Numeric(12, 6), nullable=True),
        sa.Column("return_on_assets", sa.Numeric(12, 6), nullable=True),
        sa.Column("revenue_growth", sa.Numeric(12, 6), nullable=True),
        sa.Column("earnings_growth", sa.Numeric(12, 6), nullable=True),
        sa.Column("debt_to_equity", sa.Numeric(12, 4), nullable=True),
        sa.Column("current_ratio", sa.Numeric(12, 4), nullable=True),
        sa.Column("free_cash_flow", sa.Numeric(20, 2), nullable=True),
        sa.Column("eps", sa.Numeric(12, 4), nullable=True),
        sa.Column("book_value_per_share", sa.Numeric(12, 4), nullable=True),
        sa.Column("dividend_yield", sa.Numeric(12, 6), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=True, server_default="fmp"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "as_of_date", name="uq_fundamentals_symbol_date"),
    )
    op.create_index("ix_fundamentals_symbol", "fundamentals", ["symbol"])
    op.create_index("ix_fundamentals_as_of_date", "fundamentals", ["as_of_date"])

    # --- company_profiles ---
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("exchange", sa.String(length=50), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("country", sa.String(length=50), nullable=True),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=150), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ceo", sa.String(length=150), nullable=True),
        sa.Column("employees", sa.Integer(), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("ipo_date", sa.String(length=20), nullable=True),
        sa.Column("image", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index("ix_company_profiles_symbol", "company_profiles", ["symbol"])

    # --- daily_signals ---
    # Primary key includes "signal_date" for TimescaleDB
    op.create_table(
        "daily_signals",
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("signal_date", sa.Date(), nullable=False),
        sa.Column("overall_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("value_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("quality_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("momentum_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("growth_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("signal", sa.String(length=20), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("rsi_14", sa.Numeric(8, 4), nullable=True),
        sa.Column("sma_50", sa.Numeric(18, 6), nullable=True),
        sa.Column("sma_200", sa.Numeric(18, 6), nullable=True),
        sa.Column("price_vs_sma200", sa.Numeric(8, 4), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("symbol", "signal_date"),
    )
    op.create_index("ix_daily_signals_symbol", "daily_signals", ["symbol"])
    op.create_index("ix_daily_signals_signal_date", "daily_signals", ["signal_date"])

    # Convert daily_signals to TimescaleDB hypertable
    op.execute(
        "SELECT create_hypertable('daily_signals', 'signal_date', if_not_exists => TRUE);"
    )


def downgrade() -> None:
    op.drop_table("daily_signals")
    op.drop_table("company_profiles")
    op.drop_table("fundamentals")
    op.drop_table("prices")
    op.drop_table("universe")