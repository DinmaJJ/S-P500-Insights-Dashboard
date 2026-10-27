"""
S&P 500 Insight — Streamlit dashboard
Self-contained demo: fetch data, score stocks, show rankings + charts.
"""

from __future__ import annotations

from statistics import mean

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "BRK-B", "JPM", "V", "UNH",
    "XOM", "JNJ", "WMT", "MA", "PG",
    "HD", "CVX", "MRK", "ABBV", "KO",
    "PEP", "AVGO", "COST", "LLY", "TMO",
]

st.set_page_config(
    page_title="S&P 500 Insight",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


def safe_pct(series: pd.Series, days: int) -> float | None:
    if series is None or len(series) < days + 1:
        return None
    old, new = series.iloc[-(days + 1)], series.iloc[-1]
    if pd.isna(old) or pd.isna(new) or old == 0:
        return None
    return float((new / old - 1.0) * 100.0)


def rsi(series: pd.Series, period: int = 14) -> float | None:
    if series is None or len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    if pd.isna(loss.iloc[-1]) or loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100.0 - (100.0 / (1.0 + rs)))


def percentile_rank(values: dict[str, float | None], higher_is_better: bool = True) -> dict[str, float]:
    available = {k: v for k, v in values.items() if v is not None and not pd.isna(v)}
    if not available:
        return {k: 50.0 for k in values}
    ordered = sorted(available.items(), key=lambda x: x[1], reverse=higher_is_better)
    n = len(ordered)
    scores = {sym: 100.0 * (n - 1 - i) / max(n - 1, 1) for i, (sym, _) in enumerate(ordered)}
    for k in values:
        scores.setdefault(k, 50.0)
    return scores


def invert_positive(v: float | None) -> float | None:
    if v is None or v <= 0:
        return None
    return 1.0 / v


@st.cache_data(ttl=60 * 60, show_spinner=False)
def load_symbol(symbol: str) -> dict | None:
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2y")
    if hist is None or hist.empty or len(hist) < 60:
        return None

    closes = hist["Close"].dropna()
    info = ticker.info or {}

    sma_50 = float(closes.tail(50).mean()) if len(closes) >= 50 else None
    sma_200 = float(closes.tail(200).mean()) if len(closes) >= 200 else None
    latest = float(closes.iloc[-1])
    vs200 = float((latest / sma_200 - 1) * 100) if sma_200 else None

    return {
        "symbol": symbol,
        "name": info.get("longName") or info.get("shortName") or symbol,
        "sector": info.get("sector") or "—",
        "closes": closes,
        "latest": latest,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "price_vs_sma200": vs200,
        "rsi_14": rsi(closes),
        "ret_21": safe_pct(closes, 21),
        "ret_63": safe_pct(closes, 63),
        "ret_126": safe_pct(closes, 126),
        "ret_252": safe_pct(closes, 252),
        "pe": info.get("trailingPE") or info.get("forwardPE"),
        "pb": info.get("priceToBook"),
        "ps": info.get("priceToSalesTrailing12Months"),
        "roe": info.get("returnOnEquity"),
        "roa": info.get("returnOnAssets"),
        "profit_margin": info.get("profitMargins"),
        "op_margin": info.get("operatingMargins"),
        "debt_eq": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "mcap": info.get("marketCap"),
        "summary": info.get("longBusinessSummary") or "",
    }


@st.cache_data(ttl=60 * 60, show_spinner="Fetching market data & computing scores...")
def build_rankings() -> pd.DataFrame:
    rows = []
    for sym in SYMBOLS:
        try:
            row = load_symbol(sym)
            if row:
                rows.append(row)
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    pe_s = percentile_rank({r["symbol"]: invert_positive(r["pe"]) for r in rows})
    pb_s = percentile_rank({r["symbol"]: invert_positive(r["pb"]) for r in rows})
    ps_s = percentile_rank({r["symbol"]: invert_positive(r["ps"]) for r in rows})
    roe_s = percentile_rank({r["symbol"]: r["roe"] for r in rows})
    roa_s = percentile_rank({r["symbol"]: r["roa"] for r in rows})
    pm_s = percentile_rank({r["symbol"]: r["profit_margin"] for r in rows})
    om_s = percentile_rank({r["symbol"]: r["op_margin"] for r in rows})
    cr_s = percentile_rank({r["symbol"]: r["current_ratio"] for r in rows})
    de_s = percentile_rank({r["symbol"]: invert_positive(r["debt_eq"]) for r in rows})
    m21 = percentile_rank({r["symbol"]: r["ret_21"] for r in rows})
    m63 = percentile_rank({r["symbol"]: r["ret_63"] for r in rows})
    m126 = percentile_rank({r["symbol"]: r["ret_126"] for r in rows})
    m252 = percentile_rank({r["symbol"]: r["ret_252"] for r in rows})
    vs = percentile_rank({r["symbol"]: r["price_vs_sma200"] for r in rows})

    scored = []
    for r in rows:
        s = r["symbol"]
        value = mean([pe_s[s], pb_s[s], ps_s[s]])
        quality = mean([roe_s[s], roa_s[s], pm_s[s], om_s[s], cr_s[s], de_s[s]])
        momentum = mean([m21[s], m63[s], m126[s], m252[s], vs[s]])
        overall = 0.30 * value + 0.35 * quality + 0.35 * momentum

        if overall >= 70:
            signal = "buy"
        elif overall >= 55:
            signal = "watch"
        elif overall >= 40:
            signal = "hold"
        else:
            signal = "avoid"

        scored.append({
            "symbol": s,
            "name": r["name"],
            "sector": r["sector"],
            "overall": round(overall, 1),
            "value": round(value, 1),
            "quality": round(quality, 1),
            "momentum": round(momentum, 1),
            "signal": signal,
            "price": r["latest"],
            "pe": r["pe"],
            "roe": r["roe"],
            "ret_3m": r["ret_63"],
            "vs200": r["price_vs_sma200"],
            "rsi": r["rsi_14"],
            "mcap": r["mcap"],
            "summary": r["summary"],
        })

    df = pd.DataFrame(scored).sort_values("overall", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df


def price_chart(symbol: str):
    data = load_symbol(symbol)
    if not data:
        return None
    closes = data["closes"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=closes.index, y=closes.values,
        mode="lines", name="Close",
        line=dict(color="#3b82f6", width=2),
    ))
    if data["sma_50"]:
        sma50 = closes.rolling(50).mean()
        fig.add_trace(go.Scatter(
            x=sma50.index, y=sma50.values,
            mode="lines", name="SMA 50",
            line=dict(color="#f59e0b", width=1.5, dash="dot"),
        ))
    if data["sma_200"]:
        sma200 = closes.rolling(200).mean()
        fig.add_trace(go.Scatter(
            x=sma200.index, y=sma200.values,
            mode="lines", name="SMA 200",
            line=dict(color="#a78bfa", width=1.5, dash="dash"),
        ))
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        height=320,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
    )
    return fig


st.markdown("""
<style>
  .block-container { padding-top: 1.2rem; }
  div[data-testid="stMetricValue"] { font-size: 1.4rem; }
</style>
""", unsafe_allow_html=True)

st.title("S&P 500 Insight")
st.caption("Automated scoring across value, quality, and momentum · full data pipeline project")

with st.sidebar:
    st.header("Filters")
    signal_filter = st.multiselect(
        "Signal",
        options=["buy", "watch", "hold", "avoid"],
        default=["buy", "watch", "hold", "avoid"],
    )
    top_n = st.slider("Show top N", 5, 25, 15)
    st.markdown("---")
    st.markdown("### How scoring works")
    st.markdown(
        """
- **Value (30%)** — cheaper multiples (P/E, P/B, P/S) score higher  
- **Quality (35%)** — ROE, margins, balance sheet strength  
- **Momentum (35%)** — 1–12 month returns + trend vs 200-day MA  

Signals: **buy** ≥70 · **watch** ≥55 · **hold** ≥40 · **avoid** <40
        """
    )
    st.markdown("---")
    st.markdown("**Stack:** Python · yfinance · pandas · Streamlit")
    st.markdown("**Backend project:** FastAPI · PostgreSQL · TimescaleDB · Docker")

df = build_rankings()

if df.empty:
    st.error("Could not load market data. Please refresh in a minute.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stocks scored", len(df))
c2.metric("Buy signals", int((df["signal"] == "buy").sum()))
c3.metric("Watch list", int((df["signal"] == "watch").sum()))
c4.metric("Top score", f"{df['overall'].max():.1f}")

view = df[df["signal"].isin(signal_filter)].head(top_n)

left, right = st.columns([1.25, 1])

with left:
    st.subheader("Rankings")
    show = view[["rank", "symbol", "name", "overall", "value", "quality", "momentum", "signal", "ret_3m"]].copy()
    show = show.rename(columns={
        "rank": "Rank",
        "symbol": "Symbol",
        "name": "Name",
        "overall": "Overall",
        "value": "Value",
        "quality": "Quality",
        "momentum": "Momentum",
        "signal": "Signal",
        "ret_3m": "3M %",
    })
    st.dataframe(show, use_container_width=True, hide_index=True, height=520)

with right:
    st.subheader("Stock detail")
    options = [f"{r.symbol} — {r.name}" for r in view.itertuples()]
    choice = st.selectbox("Select a stock", options, index=0 if options else 0)
    symbol = choice.split(" — ")[0] if choice else None

    if symbol:
        row = df[df["symbol"] == symbol].iloc[0]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rank", int(row["rank"]))
        m2.metric("Overall", row["overall"])
        m3.metric("Signal", row["signal"].upper())
        m4.metric("Price", f"${row['price']:.2f}")

        s1, s2, s3 = st.columns(3)
        s1.metric("Value", row["value"])
        s2.metric("Quality", row["quality"])
        s3.metric("Momentum", row["momentum"])

        fig = price_chart(symbol)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("Fundamentals & notes"):
            pe = f"{row['pe']:.1f}" if pd.notna(row["pe"]) else "—"
            roe = row["roe"]
            if pd.notna(roe):
                roe_s = f"{roe*100:.1f}%" if abs(roe) <= 2 else f"{roe:.2f}"
            else:
                roe_s = "—"
            ret = f"{row['ret_3m']:.1f}%" if pd.notna(row["ret_3m"]) else "—"
            vs = f"{row['vs200']:.1f}%" if pd.notna(row["vs200"]) else "—"
            st.write(f"**Sector:** {row['sector']}")
            st.write(f"**P/E:** {pe} · **ROE:** {roe_s} · **3M return:** {ret} · **vs SMA200:** {vs}")
            if isinstance(row["summary"], str) and row["summary"]:
                st.write(row["summary"][:500] + ("..." if len(row["summary"]) > 500 else ""))

st.markdown("---")
st.markdown(
    "Project: **S&P 500 Insight** — ETL pipeline, TimescaleDB storage, factor scoring, and interactive dashboard."
)