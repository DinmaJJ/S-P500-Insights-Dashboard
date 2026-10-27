from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, Numeric, BigInteger, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Fundamental(Base):
    """Key fundamental metrics and ratios (point-in-time snapshots)."""

    __tablename__ = "fundamentals"
    __table_args__ = (
        UniqueConstraint("symbol", "as_of_date", name="uq_fundamentals_symbol_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    # Valuation
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    peg_ratio: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    price_to_book: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    price_to_sales: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    ev_to_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))

    # Profitability
    profit_margin: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    operating_margin: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    return_on_equity: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    return_on_assets: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))

    # Growth
    revenue_growth: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    earnings_growth: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))

    # Financial health
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    current_ratio: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    free_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))

    # Per share
    eps: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    book_value_per_share: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))

    # Meta
    source: Mapped[str] = mapped_column(String(30), default="fmp")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Fundamental {self.symbol} {self.as_of_date}>"
