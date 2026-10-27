from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.universe import Universe
from app.models.prices import Price
from app.models.fundamentals import Fundamental
from app.models.signals import DailySignal
from app.models.profiles import CompanyProfile

router = APIRouter()


@router.get("/universe")
async def list_universe(
    active_only: bool = True,
    limit: int = Query(600, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Return current S&P 500 universe."""
    query = select(Universe)
    if active_only:
        query = query.where(Universe.is_active.is_(True))
    query = query.order_by(Universe.symbol).limit(limit)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "count": len(items),
        "items": [
            {
                "symbol": i.symbol,
                "name": i.name,
                "sector": i.sector,
                "sub_industry": i.sub_industry,
                "date_added": i.date_added,
                "is_active": i.is_active,
            }
            for i in items
        ],
    }


@router.get("/universe/stats")
async def universe_stats(db: AsyncSession = Depends(get_db)):
    """Simple stats about the universe."""
    total = await db.scalar(select(func.count()).select_from(Universe))
    active = await db.scalar(
        select(func.count()).select_from(Universe).where(Universe.is_active.is_(True))
    )
    price_symbols = await db.scalar(select(func.count(func.distinct(Price.symbol))))
    signal_count = await db.scalar(select(func.count()).select_from(DailySignal))
    return {
        "total": total or 0,
        "active": active or 0,
        "symbols_with_prices": price_symbols or 0,
        "signal_rows": signal_count or 0,
    }


@router.get("/rankings")
async def get_rankings(
    limit: int = Query(25, ge=1, le=100),
    signal: str | None = Query(None, description="Filter by signal: buy, watch, hold, avoid"),
    db: AsyncSession = Depends(get_db),
):
    """
    Latest stock rankings (best overall score first).
    This is the main demo endpoint.
    """
    latest = await db.scalar(select(func.max(DailySignal.signal_date)))
    if not latest:
        return {
            "signal_date": None,
            "count": 0,
            "items": [],
            "message": "No rankings yet. Run: python -m app.scripts.run_scoring",
        }

    query = (
        select(DailySignal, Universe.name, Universe.sector)
        .outerjoin(Universe, Universe.symbol == DailySignal.symbol)
        .where(DailySignal.signal_date == latest)
    )
    if signal:
        query = query.where(DailySignal.signal == signal.lower())
    query = query.order_by(DailySignal.rank.asc()).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return {
        "signal_date": latest,
        "count": len(rows),
        "items": [
            {
                "rank": s.rank,
                "symbol": s.symbol,
                "name": name,
                "sector": sector,
                "overall_score": float(s.overall_score) if s.overall_score is not None else None,
                "value_score": float(s.value_score) if s.value_score is not None else None,
                "quality_score": float(s.quality_score) if s.quality_score is not None else None,
                "momentum_score": float(s.momentum_score) if s.momentum_score is not None else None,
                "signal": s.signal,
                "rsi_14": float(s.rsi_14) if s.rsi_14 is not None else None,
                "price_vs_sma200": float(s.price_vs_sma200) if s.price_vs_sma200 is not None else None,
                "notes": s.notes,
            }
            for s, name, sector in rows
        ],
    }


@router.get("/rankings/top")
async def top_stocks(
    n: int = Query(10, ge=1, le=25),
    db: AsyncSession = Depends(get_db),
):
    """Shortcut: top N ranked stocks for demos."""
    data = await get_rankings(limit=n, signal=None, db=db)
    data["title"] = f"Top {n} ranked stocks"
    return data


@router.get("/stocks/{symbol}")
async def stock_detail(symbol: str, db: AsyncSession = Depends(get_db)):
    """Detail view for one symbol: profile, latest fundamentals, latest signal, recent prices."""
    symbol = symbol.upper()

    universe = await db.scalar(select(Universe).where(Universe.symbol == symbol))
    profile = await db.scalar(select(CompanyProfile).where(CompanyProfile.symbol == symbol))
    fund = await db.scalar(
        select(Fundamental)
        .where(Fundamental.symbol == symbol)
        .order_by(Fundamental.as_of_date.desc())
        .limit(1)
    )
    signal = await db.scalar(
        select(DailySignal)
        .where(DailySignal.symbol == symbol)
        .order_by(DailySignal.signal_date.desc())
        .limit(1)
    )
    price_count = await db.scalar(
        select(func.count()).select_from(Price).where(Price.symbol == symbol)
    )
    latest_price = await db.scalar(
        select(Price).where(Price.symbol == symbol).order_by(Price.date.desc()).limit(1)
    )

    if not universe and not price_count:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

    return {
        "symbol": symbol,
        "universe": {
            "name": universe.name if universe else None,
            "sector": universe.sector if universe else None,
            "sub_industry": universe.sub_industry if universe else None,
            "is_active": universe.is_active if universe else None,
        } if universe else None,
        "profile": {
            "name": profile.name if profile else None,
            "sector": profile.sector if profile else None,
            "industry": profile.industry if profile else None,
            "country": profile.country if profile else None,
            "website": profile.website if profile else None,
            "employees": profile.employees if profile else None,
            "description": (
                (profile.description[:400] + "...")
                if profile and profile.description and len(profile.description) > 400
                else (profile.description if profile else None)
            ),
        } if profile else None,
        "latest_price": {
            "date": latest_price.date if latest_price else None,
            "close": float(latest_price.close) if latest_price and latest_price.close is not None else None,
            "adj_close": float(latest_price.adj_close) if latest_price and latest_price.adj_close is not None else None,
            "volume": latest_price.volume if latest_price else None,
        } if latest_price else None,
        "price_rows": price_count or 0,
        "fundamentals": {
            "as_of_date": fund.as_of_date if fund else None,
            "market_cap": float(fund.market_cap) if fund and fund.market_cap is not None else None,
            "pe_ratio": float(fund.pe_ratio) if fund and fund.pe_ratio is not None else None,
            "price_to_book": float(fund.price_to_book) if fund and fund.price_to_book is not None else None,
            "price_to_sales": float(fund.price_to_sales) if fund and fund.price_to_sales is not None else None,
            "return_on_equity": float(fund.return_on_equity) if fund and fund.return_on_equity is not None else None,
            "profit_margin": float(fund.profit_margin) if fund and fund.profit_margin is not None else None,
            "debt_to_equity": float(fund.debt_to_equity) if fund and fund.debt_to_equity is not None else None,
            "current_ratio": float(fund.current_ratio) if fund and fund.current_ratio is not None else None,
            "dividend_yield": float(fund.dividend_yield) if fund and fund.dividend_yield is not None else None,
        } if fund else None,
        "signal": {
            "signal_date": signal.signal_date if signal else None,
            "rank": signal.rank if signal else None,
            "overall_score": float(signal.overall_score) if signal and signal.overall_score is not None else None,
            "value_score": float(signal.value_score) if signal and signal.value_score is not None else None,
            "quality_score": float(signal.quality_score) if signal and signal.quality_score is not None else None,
            "momentum_score": float(signal.momentum_score) if signal and signal.momentum_score is not None else None,
            "signal": signal.signal if signal else None,
            "rsi_14": float(signal.rsi_14) if signal and signal.rsi_14 is not None else None,
            "sma_50": float(signal.sma_50) if signal and signal.sma_50 is not None else None,
            "sma_200": float(signal.sma_200) if signal and signal.sma_200 is not None else None,
            "price_vs_sma200": float(signal.price_vs_sma200) if signal and signal.price_vs_sma200 is not None else None,
            "notes": signal.notes if signal else None,
        } if signal else None,
    }


@router.get("/stocks/{symbol}/prices")
async def stock_prices(
    symbol: str,
    limit: int = Query(90, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    """Recent daily prices for a symbol (most recent first)."""
    symbol = symbol.upper()
    result = await db.execute(
        select(Price)
        .where(Price.symbol == symbol)
        .order_by(Price.date.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No prices for {symbol}")

    return {
        "symbol": symbol,
        "count": len(rows),
        "items": [
            {
                "date": r.date,
                "open": float(r.open) if r.open is not None else None,
                "high": float(r.high) if r.high is not None else None,
                "low": float(r.low) if r.low is not None else None,
                "close": float(r.close) if r.close is not None else None,
                "adj_close": float(r.adj_close) if r.adj_close is not None else None,
                "volume": r.volume,
            }
            for r in rows
        ],
    }