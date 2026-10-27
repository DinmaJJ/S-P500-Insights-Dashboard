from datetime import date, datetime
from sqlalchemy import String, Date, DateTime, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Universe(Base):
    """Current and historical S&P 500 constituents."""

    __tablename__ = "universe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100))
    sub_industry: Mapped[str | None] = mapped_column(String(150))
    headquarters: Mapped[str | None] = mapped_column(String(150))
    date_added: Mapped[date | None] = mapped_column(Date)
    cik: Mapped[str | None] = mapped_column(String(20))
    founded: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Universe {self.symbol}>"
