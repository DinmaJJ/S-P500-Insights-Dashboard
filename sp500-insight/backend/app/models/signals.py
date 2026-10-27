from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class DailySignal(Base):
    """Daily analysis output: rankings, scores, and signals per symbol."""

    __tablename__ = "daily_signals"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    signal_date: Mapped[date] = mapped_column(Date, primary_key=True)

    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    value_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    momentum_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    growth_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    signal: Mapped[str | None] = mapped_column(String(20))
    rank: Mapped[int | None] = mapped_column()

    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    sma_50: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    sma_200: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    price_vs_sma200: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DailySignal {self.symbol} {self.signal_date} rank={self.rank}>"