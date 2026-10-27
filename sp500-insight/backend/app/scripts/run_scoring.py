"""
Compute value / quality / momentum scores for stocks that have price + fundamental data.
Writes results into daily_signals and prints a ranked table (demo-friendly).
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from statistics import mean

import pandas as pd
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.config import get_settings
from app.models.prices import Price
from app.models.fundamentals import Fundamental
from app.models.signals import DailySignal


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def clean_num(v):
    """Ensure DB-safe Python scalar (not numpy)."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    try:
        return float(v)
    except Exception:
        return v


def safe_pct(series: pd.Series, days: int) -> float | None:
    """Percent return over roughly `days` trading rows."""
    if series is None or len(series) < days + 1:
        return None
    old = series.iloc[-(days + 1)]
    new = series.iloc[-1]
    if old is None or old == 0 or pd.isna(old) or pd.isna(new):
        return None
    return float((new / old - 1.0) * 100.0)


def rsi(series: pd.Series, period: int = 14) -> float | None:
    if series is None or len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    if loss.iloc[-1] == 0 or pd.isna(loss.iloc[-1]):
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100.0 - (100.0 / (1.0 + rs)))


def percentile_rank(values: dict[str, float | None], higher_is_better: bool = True) -> dict[str, float]:
    """Rank available values into 0-100 scores."""
    available = {k: v for k, v in values.items() if v is not None and not pd.isna(v)}
    if not available:
        return {k: 50.0 for k in values}

    ordered = sorted(available.items(), key=lambda x: x[1], reverse=higher_is_better)
    n = len(ordered)
    scores = {}
    for i, (sym, _) in enumerate(ordered):
        scores[sym] = 100.0 * (n - 1 - i) / max(n - 1, 1)

    for k in values:
        if k not in scores:
            scores[k] = 50.0
    return scores


def invert_positive(v: float | None) -> float | None:
    """Lower PE/PB is better → invert for ranking."""
    if v is None or v <= 0:
        return None
    return 1.0 / v


def compute_for_symbol(session: Session, symbol: str) -> dict | None:
    rows = session.execute(
        select(Price.date, Price.adj_close, Price.close)
        .where(Price.symbol == symbol)
        .order_by(Price.date.asc())
    ).all()
    if len(rows) < 60:
        return None

    dates = [r.date for r in rows]
    closes = pd.Series(
        [float(r.adj_close if r.adj_close is not None else r.close) for r in rows],
        index=pd.to_datetime(dates),
    )

    latest_close = float(closes.iloc[-1])
    sma_50 = float(closes.tail(50).mean()) if len(closes) >= 50 else None
    sma_200 = float(closes.tail(200).mean()) if len(closes) >= 200 else None
    price_vs_sma200 = None
    if sma_200 and sma_200 != 0:
        price_vs_sma200 = float((latest_close / sma_200 - 1.0) * 100.0)

    ret_21 = safe_pct(closes, 21)
    ret_63 = safe_pct(closes, 63)
    ret_126 = safe_pct(closes, 126)
    ret_252 = safe_pct(closes, 252)
    rsi_14 = rsi(closes, 14)

    fund = session.execute(
        select(Fundamental)
        .where(Fundamental.symbol == symbol)
        .order_by(Fundamental.as_of_date.desc())
        .limit(1)
    ).scalar_one_or_none()

    return {
        "symbol": symbol,
        "latest_close": latest_close,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "price_vs_sma200": price_vs_sma200,
        "rsi_14": rsi_14,
        "ret_21": ret_21,
        "ret_63": ret_63,
        "ret_126": ret_126,
        "ret_252": ret_252,
        "pe": to_float(fund.pe_ratio) if fund else None,
        "pb": to_float(fund.price_to_book) if fund else None,
        "ps": to_float(fund.price_to_sales) if fund else None,
        "roe": to_float(fund.return_on_equity) if fund else None,
        "roa": to_float(fund.return_on_assets) if fund else None,
        "profit_margin": to_float(fund.profit_margin) if fund else None,
        "op_margin": to_float(fund.operating_margin) if fund else None,
        "debt_eq": to_float(fund.debt_to_equity) if fund else None,
        "current_ratio": to_float(fund.current_ratio) if fund else None,
    }


def score_universe(rows: list[dict]) -> list[dict]:
    pe_inv = {r["symbol"]: invert_positive(r["pe"]) for r in rows}
    pb_inv = {r["symbol"]: invert_positive(r["pb"]) for r in rows}
    ps_inv = {r["symbol"]: invert_positive(r["ps"]) for r in rows}
    pe_s = percentile_rank(pe_inv, True)
    pb_s = percentile_rank(pb_inv, True)
    ps_s = percentile_rank(ps_inv, True)

    roe_s = percentile_rank({r["symbol"]: r["roe"] for r in rows}, True)
    roa_s = percentile_rank({r["symbol"]: r["roa"] for r in rows}, True)
    pm_s = percentile_rank({r["symbol"]: r["profit_margin"] for r in rows}, True)
    om_s = percentile_rank({r["symbol"]: r["op_margin"] for r in rows}, True)
    cr_s = percentile_rank({r["symbol"]: r["current_ratio"] for r in rows}, True)
    de_inv = {r["symbol"]: invert_positive(r["debt_eq"]) for r in rows}
    de_s = percentile_rank(de_inv, True)

    m21 = percentile_rank({r["symbol"]: r["ret_21"] for r in rows}, True)
    m63 = percentile_rank({r["symbol"]: r["ret_63"] for r in rows}, True)
    m126 = percentile_rank({r["symbol"]: r["ret_126"] for r in rows}, True)
    m252 = percentile_rank({r["symbol"]: r["ret_252"] for r in rows}, True)
    vs200 = percentile_rank({r["symbol"]: r["price_vs_sma200"] for r in rows}, True)

    scored = []
    for r in rows:
        s = r["symbol"]
        value = mean([pe_s[s], pb_s[s], ps_s[s]])
        quality = mean([roe_s[s], roa_s[s], pm_s[s], om_s[s], cr_s[s], de_s[s]])
        momentum = mean([m21[s], m63[s], m126[s], m252[s], vs200[s]])
        overall = 0.30 * value + 0.35 * quality + 0.35 * momentum

        if overall >= 70:
            signal = "buy"
        elif overall >= 55:
            signal = "watch"
        elif overall >= 40:
            signal = "hold"
        else:
            signal = "avoid"

        notes_parts = []
        if r["pe"] is not None:
            notes_parts.append(f"PE={r['pe']:.1f}")
        if r["roe"] is not None:
            roe_val = r["roe"]
            notes_parts.append(
                f"ROE={roe_val * 100:.1f}%" if abs(roe_val) <= 2 else f"ROE={roe_val:.1f}"
            )
        if r["ret_63"] is not None:
            notes_parts.append(f"3M={r['ret_63']:.1f}%")
        if r["price_vs_sma200"] is not None:
            notes_parts.append(f"vs200={r['price_vs_sma200']:.1f}%")

        scored.append({
            **r,
            "value_score": round(float(value), 2),
            "quality_score": round(float(quality), 2),
            "momentum_score": round(float(momentum), 2),
            "growth_score": None,
            "overall_score": round(float(overall), 2),
            "signal": signal,
            "notes": ", ".join(notes_parts) if notes_parts else None,
        })

    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    for i, row in enumerate(scored, 1):
        row["rank"] = i
    return scored


def ensure_unique_index(session: Session) -> None:
    """Make sure upserts work even if migration constraint name differs."""
    session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_signals_symbol_date "
        "ON daily_signals (symbol, signal_date);"
    ))
    session.commit()


def save_signals(session: Session, scored: list[dict], signal_date: date) -> int:
    count = 0
    for row in scored:
        stmt = insert(DailySignal).values(
            symbol=row["symbol"],
            signal_date=signal_date,
            overall_score=clean_num(row["overall_score"]),
            value_score=clean_num(row["value_score"]),
            quality_score=clean_num(row["quality_score"]),
            momentum_score=clean_num(row["momentum_score"]),
            growth_score=clean_num(row["growth_score"]),
            signal=row["signal"],
            rank=int(row["rank"]) if row["rank"] is not None else None,
            rsi_14=clean_num(row["rsi_14"]),
            sma_50=clean_num(row["sma_50"]),
            sma_200=clean_num(row["sma_200"]),
            price_vs_sma200=clean_num(row["price_vs_sma200"]),
            notes=row["notes"],
            created_at=utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "signal_date"],
            set_={
                "overall_score": stmt.excluded.overall_score,
                "value_score": stmt.excluded.value_score,
                "quality_score": stmt.excluded.quality_score,
                "momentum_score": stmt.excluded.momentum_score,
                "growth_score": stmt.excluded.growth_score,
                "signal": stmt.excluded.signal,
                "rank": stmt.excluded.rank,
                "rsi_14": stmt.excluded.rsi_14,
                "sma_50": stmt.excluded.sma_50,
                "sma_200": stmt.excluded.sma_200,
                "price_vs_sma200": stmt.excluded.price_vs_sma200,
                "notes": stmt.excluded.notes,
                "created_at": utcnow(),
            },
        )
        session.execute(stmt)
        count += 1
    session.commit()
    return count


def print_table(scored: list[dict]) -> None:
    print()
    print(f"{'Rank':<5} {'Symbol':<8} {'Overall':>8} {'Value':>7} {'Quality':>8} {'Mom':>7} {'Signal':<7} Notes")
    print("-" * 90)
    for r in scored:
        print(
            f"{r['rank']:<5} {r['symbol']:<8} {r['overall_score']:>8.1f} "
            f"{r['value_score']:>7.1f} {r['quality_score']:>8.1f} {r['momentum_score']:>7.1f} "
            f"{r['signal']:<7} {r['notes'] or ''}"
        )
    print("-" * 90)


def main() -> None:
    settings = get_settings()
    db_url = os.getenv("DATABASE_URL_SYNC") or settings.database_url_sync
    engine = create_engine(db_url)
    signal_date = date.today()

    print("Loading symbols with price history...")
    with Session(engine) as session:
        ensure_unique_index(session)

        symbols = session.execute(
            select(Price.symbol).distinct().order_by(Price.symbol)
        ).scalars().all()
        print(f"Found {len(symbols)} symbols with prices")

        features = []
        for sym in symbols:
            feat = compute_for_symbol(session, sym)
            if feat:
                features.append(feat)
            else:
                print(f"  skip {sym}: insufficient history")

        if not features:
            print("No symbols to score.")
            sys.exit(1)

        scored = score_universe(features)
        n = save_signals(session, scored, signal_date)
        print(f"\nSaved {n} rows into daily_signals for {signal_date}")
        print_table(scored)


if __name__ == "__main__":
    main()