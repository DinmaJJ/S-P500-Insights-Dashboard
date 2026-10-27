from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CompanyProfile(Base):
    """Static / slowly-changing company profile information."""

    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255))
    exchange: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str | None] = mapped_column(String(10))
    country: Mapped[str | None] = mapped_column(String(50))
    sector: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    ceo: Mapped[str | None] = mapped_column(String(150))
    employees: Mapped[int | None] = mapped_column(Integer)
    website: Mapped[str | None] = mapped_column(String(255))
    ipo_date: Mapped[str | None] = mapped_column(String(20))
    image: Mapped[str | None] = mapped_column(String(500))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<CompanyProfile {self.symbol}>"
