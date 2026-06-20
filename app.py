import io
import os
import sys
import json
import math
import traceback
import platform
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="InvestAI v11 Investment Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "InvestAI v11 Investment Intelligence"
WATCHLIST_FILE = "watchlist.csv"
OSLO_UNIVERSE_FILE = "oslo_universe.csv"
PORTFOLIO_FILE = "portfolio.csv"
EARNINGS_FILE = "earnings_calendar.csv"
INSIDER_FILE = "insider_watch.csv"
NOTES_FILE = "notes.csv"

# -----------------------------
# UI helpers
# -----------------------------
def clamp(x, lo=0, hi=100):
    try:
        if pd.isna(x):
            return 0
        return max(lo, min(hi, float(x)))
    except Exception:
        return 0


def fmt_pct(x, digits=1):
    try:
        if pd.isna(x):
            return "–"
        return f"{float(x):+.{digits}f}%"
    except Exception:
        return "–"


def fmt_num(x, digits=1):
    try:
        if pd.isna(x):
            return "–"
        return f"{float(x):,.{digits}f}".replace(",", " ")
    except Exception:
        return "–"


def fmt_money(x):
    try:
        if pd.isna(x) or float(x) <= 0:
            return "–"
        x = float(x)
        if x >= 1e12:
            return f"{x/1e12:.1f} tn"
        if x >= 1e9:
            return f"{x/1e9:.1f} mrd"
        if x >= 1e6:
            return f"{x/1e6:.1f} mill"
        return f"{x:,.0f}".replace(",", " ")
    except Exception:
        return "–"


def status_label(score):
    s = clamp(score)
    if s >= 80:
        return "Sterk"
    if s >= 65:
        return "God"
    if s >= 50:
        return "Nøytral"
    if s >= 35:
        return "Svak"
    return "Kritisk"


def risk_label(score):
    s = clamp(score)
    if s >= 75:
        return "Høy"
    if s >= 55:
        return "Moderat/høy"
    if s >= 35:
        return "Moderat"
    return "Lav/moderat"


def score_color(score, reverse=False):
    s = clamp(score)
    if reverse:
        s = 100 - s
    if s >= 75:
        return "#22c55e"
    if s >= 55:
        return "#84cc16"
    if s >= 40:
        return "#f59e0b"
    return "#ef4444"


def copy_button_html(text, label="📋 Kopier"):
    txt = json.dumps(str(text))
    lab = json.dumps(label)
    return f"""
    <button id="copyBtn" style="width:100%;padding:0.70rem 1rem;border-radius:12px;border:1px solid rgba(148,163,184,.35);background:#2563eb;color:white;font-weight:800;cursor:pointer;">{label}</button>
    <div id="copyStatus" style="font-size:0.82rem;margin-top:0.4rem;color:#64748b;"></div>
    <script>
    const b=document.getElementById('copyBtn'); const s=document.getElementById('copyStatus'); const t={txt}; b.innerText={lab};
    b.onclick=async()=>{{try{{await navigator.clipboard.writeText(t);s.innerText='Kopiert. Lim inn i ChatGPT.';}}catch(e){{s.innerText='Kunne ikke kopiere automatisk. Marker teksten under og kopier manuelt.';}}}};
    </script>
    """


def apply_css(mode):
    dark = mode == "Mørk"
    bg = "#020617" if dark else "#f8fafc"
    panel = "#0f172a" if dark else "#ffffff"
    panel2 = "#111827" if dark else "#f1f5f9"
    text = "#e5e7eb" if dark else "#0f172a"
    muted = "#94a3b8" if dark else "#475569"
    border = "rgba(148,163,184,.22)" if dark else "rgba(15,23,42,.10)"
    st.markdown(f"""
    <style>
    :root {{ --bg:{bg}; --panel:{panel}; --panel2:{panel2}; --text:{text}; --muted:{muted}; --border:{border}; }}
    .stApp {{ background: var(--bg); color: var(--text); }}
    h1,h2,h3,h4,p,span,div,label {{ color: var(--text); }}
    [data-testid="stSidebar"] {{ background: {panel}; border-right:1px solid var(--border); }}
    .block-container {{ padding-top: 1.2rem; max-width: 1450px; }}
    .topbar {{ position: sticky; top: 0; z-index: 999; background: linear-gradient(90deg, {panel}, {panel2}); border:1px solid var(--border); border-radius:18px; padding: 1rem 1.2rem; margin-bottom:1rem; box-shadow:0 10px 30px rgba(0,0,0,.08); }}
    .topbar-title {{ font-size:1.35rem; font-weight:900; letter-spacing:-.03em; }}
    .subtle {{ color:var(--muted); font-size:.92rem; }}
    .metric-card {{ background:var(--panel); border:1px solid var(--border); border-radius:18px; padding:1rem; min-height:108px; box-shadow:0 10px 24px rgba(0,0,0,.06); }}
    .metric-title {{ color:var(--muted); font-size:.78rem; text-transform:uppercase; font-weight:800; letter-spacing:.06em; }}
    .metric-value {{ font-size:1.65rem; font-weight:900; line-height:1.1; margin-top:.35rem; }}
    .metric-note {{ color:var(--muted); font-size:.85rem; margin-top:.35rem; }}
    .stock-card {{ background:var(--panel); border:1px solid var(--border); border-radius:20px; padding:1rem; margin:0.35rem 0 0.85rem 0; box-shadow:0 10px 26px rgba(0,0,0,.07); }}
    .stock-head {{ display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }}
    .ticker {{ font-size:1.15rem; font-weight:950; letter-spacing:-.02em; }}
    .company {{ color:var(--muted); font-size:.92rem; margin-top:.15rem; }}
    .pill {{ display:inline-block; padding:.28rem .55rem; border-radius:999px; background:rgba(37,99,235,.12); color:#60a5fa; font-size:.78rem; font-weight:800; margin:.15rem .25rem .15rem 0; }}
    .score-badge {{ border-radius:14px; padding:.45rem .65rem; color:white; font-weight:950; min-width:68px; text-align:center; }}
    .mini-grid {{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:.55rem; margin-top:.85rem; }}
    .mini-cell {{ background:var(--panel2); border:1px solid var(--border); border-radius:14px; padding:.65rem; }}
    .mini-label {{ color:var(--muted); font-size:.74rem; font-weight:800; text-transform:uppercase; }}
    .mini-value {{ font-weight:900; margin-top:.15rem; }}
    .section-card {{ background:var(--panel); border:1px solid var(--border); border-radius:20px; padding:1rem; margin-bottom:1rem; }}
    .redflag {{ background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.25); border-radius:14px; padding:.65rem .8rem; margin:.45rem 0; }}
    .positive {{ background:rgba(34,197,94,.12); border:1px solid rgba(34,197,94,.25); border-radius:14px; padding:.65rem .8rem; margin:.45rem 0; }}
    .thesis {{ background:linear-gradient(135deg, rgba(37,99,235,.14), rgba(14,165,233,.08)); border:1px solid rgba(96,165,250,.28); border-radius:18px; padding:1rem; margin:.6rem 0; }}
    .opportunity {{ background:var(--panel); border:1px solid var(--border); border-radius:18px; padding:1rem; margin:.6rem 0; box-shadow:0 10px 24px rgba(0,0,0,.06); }}
    @media (max-width: 768px) {{
      .mini-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
      .metric-value {{ font-size:1.25rem; }}
      .stock-head {{ display:block; }}
    }}
    </style>
    """, unsafe_allow_html=True)


def kpi_card(title, value, note=""):
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-title">{title}</div>
      <div class="metric-value">{value}</div>
      <div class="metric-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# Data loading and validation
# -----------------------------
def ensure_csv_files():
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=["ticker", "shares", "cost_price", "note"]).to_csv(PORTFOLIO_FILE, index=False)
    if not os.path.exists(WATCHLIST_FILE) and os.path.exists(OSLO_UNIVERSE_FILE):
        pd.read_csv(OSLO_UNIVERSE_FILE).head(40).to_csv(WATCHLIST_FILE, index=False)
    if not os.path.exists(NOTES_FILE):
        pd.DataFrame(columns=["ticker", "note", "updated"]).to_csv(NOTES_FILE, index=False)


@st.cache_data(ttl=3600, show_spinner=False)
def load_universe():
    ensure_csv_files()
    frames = []
    for path in [OSLO_UNIVERSE_FILE, WATCHLIST_FILE]:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                frames.append(df)
            except Exception:
                pass
    if not frames:
        return pd.DataFrame({
            "ticker": ["EQNR.OL", "DNB.OL", "KOG.OL", "NOD.OL", "KIT.OL"],
            "name": ["Equinor", "DNB", "Kongsberg Gruppen", "Nordic Semiconductor", "Kitron"],
            "sector": ["Energi", "Finans", "Forsvar / Teknologi", "Semiconductor / IoT", "Industri / EMS"],
            "market": ["Oslo Børs"] * 5,
            "segment": ["Hovedliste"] * 5,
        })
    df = pd.concat(frames, ignore_index=True)
    df.columns = [c.strip().lower() for c in df.columns]
    for col in ["ticker", "name", "sector", "market", "segment"]:
        if col not in df.columns:
            df[col] = ""
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df = df[df["ticker"].str.len() > 0]
    df = df.drop_duplicates("ticker")
    return df[["ticker", "name", "sector", "market", "segment"]].reset_index(drop=True)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_one(ticker, name="", sector="", market="", segment=""):
    out = {
        "ticker": ticker, "name": name or ticker, "sector": sector or "Ukjent", "market": market or "Oslo", "segment": segment or "",
        "price": np.nan, "daily_return": np.nan, "return_1m": np.nan, "return_3m": np.nan, "return_1y": np.nan,
        "volatility": np.nan, "max_drawdown": np.nan, "market_cap": np.nan, "pe": np.nan, "ps": np.nan,
        "debt_to_equity": np.nan, "revenue_growth": np.nan, "profit_margin": np.nan,
        "data_quality": "Lav", "error": "",
    }
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            close = hist["Close"].dropna()
            if len(close) >= 2:
                out["price"] = float(close.iloc[-1])
                out["daily_return"] = float((close.iloc[-1] / close.iloc[-2] - 1) * 100)
                if len(close) > 22:
                    out["return_1m"] = float((close.iloc[-1] / close.iloc[-22] - 1) * 100)
                if len(close) > 63:
                    out["return_3m"] = float((close.iloc[-1] / close.iloc[-63] - 1) * 100)
                out["return_1y"] = float((close.iloc[-1] / close.iloc[0] - 1) * 100)
                daily = close.pct_change().dropna()
                if len(daily) > 20:
                    out["volatility"] = float(daily.std() * np.sqrt(252) * 100)
                peak = close.cummax()
                dd = (close / peak - 1) * 100
                out["max_drawdown"] = float(dd.min())
                out["data_quality"] = "God"
        try:
            info = t.get_info() or {}
        except Exception:
            info = {}
        out["market_cap"] = info.get("marketCap", np.nan) or np.nan
        out["pe"] = info.get("trailingPE", np.nan) or info.get("forwardPE", np.nan) or np.nan
        out["ps"] = info.get("priceToSalesTrailing12Months", np.nan) or np.nan
        out["debt_to_equity"] = info.get("debtToEquity", np.nan) or np.nan
        out["revenue_growth"] = (info.get("revenueGrowth", np.nan) * 100) if info.get("revenueGrowth", None) is not None else np.nan
        out["profit_margin"] = (info.get("profitMargins", np.nan) * 100) if info.get("profitMargins", None) is not None else np.nan
    except Exception as e:
        out["error"] = str(e)[:180]
    return out


def to_numeric_series(df, column, default=np.nan):
    """Return a clean numeric Series even if yfinance/CSV gives text values.

    Handles strings like "N/A", "None", "1,234.5", "12%" and empty values.
    This prevents Streamlit Cloud crashes when free market data changes format.
    """
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype="float64")
    s = df[column].copy()
    if s.dtype == "object":
        s = (
            s.astype(str)
            .str.strip()
            .str.replace("%", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", "", regex=False)
            .replace({"": np.nan, "nan": np.nan, "None": np.nan, "N/A": np.nan, "-": np.nan})
        )
    return pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)




def sector_theme(sector_text):
    sector = str(sector_text or "").lower()
    themes = []
    if any(k in sector for k in ["ai", "semiconductor", "software", "teknologi", "iot", "edtech", "digital"]):
        themes.append("AI / Digitalisering")
    if any(k in sector for k in ["forsvar", "defence", "kongsberg"]):
        themes.append("Forsvar")
    if any(k in sector for k in ["energi", "olje", "offshore", "shipping", "fornybar", "hydrogen", "carbon", "ccs"]):
        themes.append("Energi / Råvarer")
    if any(k in sector for k in ["helse", "medtech", "biotech", "pharma", "diagnostikk"]):
        themes.append("Helse / Medtech")
    if any(k in sector for k in ["bank", "finans", "forsikring", "megling"]):
        themes.append("Finans")
    if not themes:
        themes.append("Generell")
    return ", ".join(themes)


def classify_stock_row(row):
    """Classify a scored row into practical InvestAI categories."""
    inv = clamp(row.get("Investment Score", 0))
    rocket = clamp(row.get("Rocket Score", 0))
    mom = clamp(row.get("Momentum Score", 0))
    val = clamp(row.get("Value Score", 0))
    qual = clamp(row.get("Quality Score", 0))
    risk = clamp(row.get("Risk Score", 0))
    r1y = row.get("return_1y", 0)
    rev = row.get("revenue_growth", 0)
    pe = row.get("pe", np.nan)
    segment = str(row.get("segment", "")).lower()
    sector = str(row.get("sector", "")).lower()
    mcap = row.get("market_cap", np.nan)

    tags = []
    if qual >= 70 and risk <= 60:
        tags.append("Kvalitet")
    if val >= 72:
        tags.append("Verdi")
    if mom >= 70:
        tags.append("Momentum")
    if rocket >= 75 and risk >= 55:
        tags.append("Rakett")
    if risk <= 45 and qual >= 55:
        tags.append("Lavere risiko")
    if pd.notna(r1y) and float(r1y) < -25 and (mom >= 45 or val >= 65):
        tags.append("Turnaround")
    if pd.notna(pe) and float(pe) > 0 and float(pe) < 14 and risk <= 65:
        tags.append("Utbytte / Value-kandidat")
    theme = sector_theme(sector)
    for t in [x.strip() for x in theme.split(",")]:
        if t and t != "Generell":
            tags.append(t)

    if not tags:
        tags.append("Observasjon")

    # Practical universe bucket after scoring
    if qual >= 68 and risk <= 60 and "growth" not in segment:
        bucket = "Kvalitetsunivers"
    elif "growth" in segment or rocket >= 72 or risk >= 70 or any(k in sector for k in ["hydrogen", "biotech", "medtech", "forsvar", "ai", "semiconductor", "fornybar"]):
        bucket = "Rakettunivers"
    elif "hovedliste" in segment or "oslo" in str(row.get("market", "")).lower():
        bucket = "Oslo Børs"
    else:
        bucket = "Full Norge"

    if inv >= 80:
        tier = "A · Sterk kandidat"
    elif inv >= 68:
        tier = "B · Interessant"
    elif rocket >= 75:
        tier = "C · Spekulativ rakett"
    elif risk >= 75:
        tier = "D · Høy risiko"
    else:
        tier = "E · Følg med"

    why = []
    if inv >= 70: why.append("høy samlet score")
    if rocket >= 75: why.append("høyt rakettpotensial")
    if mom >= 70: why.append("sterkt momentum")
    if val >= 72: why.append("attraktiv verdsettelse")
    if qual >= 70: why.append("god kvalitet")
    if risk >= 70: why.append("høy risiko")
    if not why: why.append("blandet modellbilde")

    return pd.Series({
        "Kategori": ", ".join(dict.fromkeys(tags)),
        "Univers": bucket,
        "Tier": tier,
        "Tema": theme,
        "Hvorfor på listen": "; ".join(why),
    })


def add_investai_classification(df):
    if df.empty:
        for col in ["Kategori", "Univers", "Tier", "Tema", "Hvorfor på listen"]:
            df[col] = ""
        return df
    classified = df.apply(classify_stock_row, axis=1)
    return pd.concat([df.reset_index(drop=True), classified.reset_index(drop=True)], axis=1)


def filter_universe_pre_screen(df, mode):
    """Pre-filter based on available CSV metadata before expensive yfinance calls."""
    out = df.copy()
    seg = out.get("segment", pd.Series("", index=out.index)).astype(str).str.lower()
    sec = out.get("sector", pd.Series("", index=out.index)).astype(str).str.lower()
    if mode == "Kvalitet":
        out = out[seg.str.contains("hovedliste", na=False)]
        risky = sec.str.contains("hydrogen|biotech|høy risiko|spec|venture|crypto|mining", na=False)
        out = out[~risky]
    elif mode == "Oslo Børs":
        out = out[seg.str.contains("hovedliste", na=False)]
    elif mode == "Rakettunivers":
        rocket_terms = "growth|hydrogen|fornybar|teknologi|semiconductor|software|ai|iot|forsvar|medtech|biotech|miljø|carbon|ccs|shipping|offshore"
        preferred = out[seg.str.contains("growth", na=False) | sec.str.contains(rocket_terms, na=False)]
        rest = out.drop(preferred.index, errors="ignore")
        out = pd.concat([preferred, rest], ignore_index=True)
    # Full Norge = no filtering
    if out.empty:
        return df.copy()
    return out.reset_index(drop=True)

def score_dataframe(df):
    df = df.copy()

    numeric_columns = [
        "return_1y", "return_3m", "daily_return", "volatility", "max_drawdown",
        "pe", "ps", "debt_to_equity", "revenue_growth", "profit_margin", "market_cap", "last_price"
    ]
    for col in numeric_columns:
        df[col] = to_numeric_series(df, col)

    r1y = df["return_1y"].fillna(0)
    r3m = df["return_3m"].fillna(0)
    dly = df["daily_return"].fillna(0)
    vol_median = df["volatility"].median() if df["volatility"].notna().any() else 45
    vol = df["volatility"].fillna(vol_median)
    dd = df["max_drawdown"].fillna(-40)
    pe = df["pe"]
    ps = df["ps"]
    debt = df["debt_to_equity"]
    rev = df["revenue_growth"].fillna(0)
    margin = df["profit_margin"].fillna(0)

    df["Momentum Score"] = (50 + r1y * 0.35 + r3m * 0.65 + dly * 0.6).apply(clamp)
    value_pe = pe.apply(lambda x: 70 if pd.isna(x) else 90 if 0 < float(x) < 12 else 75 if float(x) < 20 else 55 if float(x) < 35 else 35)
    value_ps = ps.apply(lambda x: 65 if pd.isna(x) else 90 if 0 < float(x) < 1.5 else 75 if float(x) < 3 else 55 if float(x) < 6 else 35)
    df["Value Score"] = (value_pe * 0.55 + value_ps * 0.45).apply(clamp)
    risk_raw = 25 + vol * 0.75 + abs(dd) * 0.45 + debt.fillna(70) * 0.05
    df["Risk Score"] = risk_raw.apply(clamp)
    quality_raw = 50 + margin * 1.2 + rev * 0.35 - df["Risk Score"] * 0.15
    df["Quality Score"] = quality_raw.apply(clamp)
    rocket_raw = df["Momentum Score"] * 0.42 + np.clip(rev + 35, 0, 100) * 0.25 + df["Value Score"] * 0.18 + (100 - df["Risk Score"]) * 0.10 + 8
    df["Rocket Score"] = rocket_raw.apply(clamp)
    df["Investment Score"] = (
        df["Momentum Score"] * 0.25 + df["Value Score"] * 0.22 + df["Quality Score"] * 0.25 + df["Rocket Score"] * 0.18 + (100 - df["Risk Score"]) * 0.10
    ).apply(clamp)
    df = add_investai_classification(df)
    df = add_conviction_columns(df)
    return df


@st.cache_data(ttl=1800, show_spinner=True)
def run_screen(tickers_df, max_count):
    rows = []
    use = tickers_df.head(max_count).copy()
    for _, r in use.iterrows():
        rows.append(fetch_one(r["ticker"], r.get("name", ""), r.get("sector", ""), r.get("market", ""), r.get("segment", "")))
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return score_dataframe(df)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_history(ticker):
    try:
        hist = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
        if hist is None or hist.empty:
            return pd.DataFrame()
        hist = hist.reset_index()
        if "Date" not in hist.columns:
            hist = hist.rename(columns={hist.columns[0]: "Date"})
        return hist
    except Exception:
        return pd.DataFrame()

# -----------------------------
# Analysis text helpers
# -----------------------------
def explain_score(row):
    points = []
    if row.get("Investment Score", 0) >= 75:
        points.append("Høy samlet score drevet av kombinasjonen momentum, kvalitet og/eller verdsettelse.")
    if row.get("Momentum Score", 0) >= 70:
        points.append("Sterk markedstrend: aksjen har positiv kursutvikling relativt til egen historikk.")
    elif row.get("Momentum Score", 0) < 40:
        points.append("Svak markedstrend: momentum trekker ned totalbildet.")
    if row.get("Value Score", 0) >= 70:
        points.append("Verdsettelsen ser relativt attraktiv ut på tilgjengelige multipler.")
    if row.get("Quality Score", 0) >= 70:
        points.append("Kvalitetsscoren indikerer bedre margin/vekst-bilde enn gjennomsnittet i datasettet.")
    if row.get("Risk Score", 0) >= 70:
        points.append("Risikoen er høy: volatilitet, drawdown eller balanseindikatorer trekker opp risikobildet.")
    if not points:
        points.append("Scoren er blandet. Aksjen trenger mer fundamental analyse før den vurderes videre.")
    return points


def red_flags(row):
    flags = []
    if row.get("Risk Score", 0) >= 75:
        flags.append("Høyt risikonivå i modellen")
    if row.get("max_drawdown", 0) <= -45:
        flags.append(f"Stort fall fra topp siste år ({fmt_pct(row.get('max_drawdown'), 0)})")
    if row.get("volatility", 0) >= 65:
        flags.append(f"Høy volatilitet ({fmt_pct(row.get('volatility'), 0)})")
    if pd.notna(row.get("debt_to_equity", np.nan)) and row.get("debt_to_equity", 0) > 180:
        flags.append("Høy gjeldsgrad / balanse kan være sårbar")
    if row.get("return_1y", 0) < -30:
        flags.append("Negativ 1 års kursutvikling")
    if pd.isna(row.get("market_cap", np.nan)):
        flags.append("Manglende markedsverdi fra gratis datakilde")
    return flags


def positives(row):
    ps = []
    if row.get("Investment Score", 0) >= 70:
        ps.append("Sterk samlet modellscore")
    if row.get("Rocket Score", 0) >= 75:
        ps.append("Høyt rakettpotensial i screeningen")
    if row.get("Momentum Score", 0) >= 70:
        ps.append("Positiv markedstrend")
    if row.get("Value Score", 0) >= 70:
        ps.append("Attraktiv relativ verdsettelse")
    if pd.notna(row.get("revenue_growth", np.nan)) and row.get("revenue_growth", 0) > 15:
        ps.append("Sterk rapportert omsetningsvekst")
    if not ps:
        ps.append("Ingen tydelig modellmessig styrke — bruk aksjen som observasjonscase.")
    return ps


def scenario_estimates(row):
    price = row.get("price", np.nan)
    if pd.isna(price) or price <= 0:
        return {"bear": np.nan, "base": np.nan, "bull": np.nan}
    risk = clamp(row.get("Risk Score", 50))
    inv = clamp(row.get("Investment Score", 50))
    rocket = clamp(row.get("Rocket Score", 50))
    downside = 0.12 + risk / 250
    base_up = (inv - 50) / 180
    bull_up = 0.18 + rocket / 140
    return {"bear": price * (1 - downside), "base": price * (1 + base_up), "bull": price * (1 + bull_up)}




def conviction_score(row):
    """Decision-oriented score: quality + growth + valuation + momentum - risk + catalysts."""
    quality = clamp(row.get("Quality Score", 50))
    momentum = clamp(row.get("Momentum Score", 50))
    value = clamp(row.get("Value Score", 50))
    risk_inverse = 100 - clamp(row.get("Risk Score", 50))
    rocket = clamp(row.get("Rocket Score", 50))
    growth = clamp(50 + float(row.get("revenue_growth", 0) or 0) * 0.8)
    catalyst = clamp((rocket * 0.55) + (momentum * 0.30) + (quality * 0.15))
    score = quality * 0.25 + growth * 0.20 + value * 0.15 + momentum * 0.15 + risk_inverse * 0.15 + catalyst * 0.10
    return clamp(score)


def conviction_label(score):
    s = clamp(score)
    if s >= 90:
        return "Elite"
    if s >= 80:
        return "Sterk kandidat"
    if s >= 70:
        return "Kjøpskandidat"
    if s >= 60:
        return "Følg tett"
    return "Lav prioritet"


def upside_label(row):
    rocket = clamp(row.get("Rocket Score", 0))
    inv = clamp(row.get("Investment Score", 0))
    if rocket >= 82 and inv >= 65:
        return "Svært høy"
    if rocket >= 70:
        return "Høy"
    if inv >= 65:
        return "Moderat"
    return "Usikker"


def conviction_drivers(row):
    drivers = []
    if clamp(row.get("Quality Score", 0)) >= 70:
        drivers.append("kvalitet")
    if clamp(row.get("Momentum Score", 0)) >= 70:
        drivers.append("momentum")
    if clamp(row.get("Value Score", 0)) >= 70:
        drivers.append("verdsettelse")
    if clamp(row.get("Rocket Score", 0)) >= 75:
        drivers.append("oppsidepotensial")
    if clamp(row.get("Risk Score", 0)) <= 45:
        drivers.append("lavere risiko")
    if pd.notna(row.get("revenue_growth", np.nan)) and row.get("revenue_growth", 0) > 15:
        drivers.append("vekst")
    return drivers or ["blandet, men interessant modellbilde"]


def red_flag_engine(row):
    flags = list(red_flags(row))
    if clamp(row.get("Quality Score", 0)) < 35:
        flags.append("Lav kvalitetsscore")
    if clamp(row.get("Value Score", 0)) < 35 and pd.notna(row.get("pe", np.nan)):
        flags.append("Krevende verdsettelse relativt til tilgjengelige multipler")
    if row.get("return_3m", 0) < -20:
        flags.append("Svak 3-måneders kursutvikling")
    if pd.notna(row.get("profit_margin", np.nan)) and row.get("profit_margin", 0) < -10:
        flags.append("Negativ margin / lønnsomhetspress")
    return list(dict.fromkeys(flags))


def investment_thesis(row):
    name = row.get("name", row.get("ticker", "Selskapet"))
    ticker = row.get("ticker", "")
    sector = row.get("sector", "ukjent sektor")
    conv = conviction_label(row.get("Conviction Score", conviction_score(row)))
    drivers = ", ".join(conviction_drivers(row)[:4])
    risk = risk_label(row.get("Risk Score", 0)).lower()
    return f"{name} ({ticker}) er et {conv.lower()} investeringscase innen {sector}. Modellen peker særlig på {drivers}, mens risikobildet vurderes som {risk}. Caset bør brukes som et startpunkt for videre fundamental analyse, ikke som en automatisk kjøpsanbefaling."


def bull_case_points(row):
    pts = positives(row)
    if clamp(row.get("Conviction Score", 0)) >= 80:
        pts.insert(0, "Høy Conviction Score indikerer god kombinasjon av kvalitet, momentum og risikojustert oppside.")
    return list(dict.fromkeys(pts))[:5]


def bear_case_points(row):
    flags = red_flag_engine(row)
    if not flags:
        flags = ["Gratisdata viser ingen åpenbare røde flagg, men fundamental rapportanalyse er fortsatt nødvendig."]
    return flags[:5]


def add_conviction_columns(df):
    if df.empty:
        return df
    df = df.copy()
    df["Conviction Score"] = df.apply(conviction_score, axis=1).apply(clamp)
    df["Conviction"] = df["Conviction Score"].apply(conviction_label)
    df["Oppside"] = df.apply(upside_label, axis=1)
    df["Investment Thesis"] = df.apply(investment_thesis, axis=1)
    df["Red Flags"] = df.apply(lambda r: "; ".join(red_flag_engine(r)) or "Ingen tydelige røde flagg", axis=1)
    return df

def make_prompt(row):
    flags = "; ".join(red_flags(row)) or "Ingen tydelige røde flagg fra modellen"
    strengths = "; ".join(positives(row))
    scen = scenario_estimates(row)
    return f"""Analyser {row.get('name', row.get('ticker'))} ({row.get('ticker')}) som investeringscase på norsk.

Bruk en profesjonell equity research-struktur:
1. Kort investment case
2. Bull case
3. Bear case
4. Nøkkeltall og kvalitet
5. Verdsettelse relativt til vekst og risiko
6. Katalysatorer neste 6–24 måneder
7. Risiko og røde flagg
8. Scenarioanalyse: bear/base/bull
9. Hvem aksjen passer for

Data fra InvestAI v11:
- Sektor: {row.get('sector', 'Ukjent')}
- Marked: {row.get('market', 'Ukjent')}
- InvestAI-kategori: {row.get('Kategori', 'Ukjent')}
- InvestAI-tier: {row.get('Tier', 'Ukjent')}
- Hvorfor på listen: {row.get('Hvorfor på listen', 'Ukjent')}
- Siste kurs: {fmt_num(row.get('price'))}
- 1 års avkastning: {fmt_pct(row.get('return_1y'))}
- 3 mnd avkastning: {fmt_pct(row.get('return_3m'))}
- Conviction Score: {fmt_num(row.get('Conviction Score'))}/100 ({row.get('Conviction', 'Ukjent')})
- Investment Thesis: {row.get('Investment Thesis', 'Ukjent')}
- Investment Score: {fmt_num(row.get('Investment Score'))}/100
- Rocket Score: {fmt_num(row.get('Rocket Score'))}/100
- Momentum Score: {fmt_num(row.get('Momentum Score'))}/100
- Value Score: {fmt_num(row.get('Value Score'))}/100
- Quality Score: {fmt_num(row.get('Quality Score'))}/100
- Risk Score: {fmt_num(row.get('Risk Score'))}/100
- P/E: {fmt_num(row.get('pe'))}
- P/S: {fmt_num(row.get('ps'))}
- Markedsverdi: {fmt_money(row.get('market_cap'))}
- Modellstyrker: {strengths}
- Røde flagg: {flags}
- Modellscenario kurs: bear {fmt_num(scen['bear'])}, base {fmt_num(scen['base'])}, bull {fmt_num(scen['bull'])}

Skill tydelig mellom fakta, modellestimat og egen vurdering. Ikke gi personlig finansiell rådgivning."""


def render_stock_card(row):
    c = score_color(row.get("Conviction Score", row.get("Investment Score", 0)))
    st.markdown(f"""
    <div class="stock-card">
      <div class="stock-head">
        <div>
          <div class="ticker">{row.get('ticker','')}</div>
          <div class="company">{row.get('name','')} · {row.get('sector','Ukjent')}</div>
          <span class="pill">{row.get('Conviction', status_label(row.get('Investment Score', 0)))}</span>
          <span class="pill">Risiko: {risk_label(row.get('Risk Score', 0))}</span>
          <span class="pill">{row.get('Tier','')}</span>
        </div>
        <div class="score-badge" style="background:{c};">{fmt_num(row.get('Conviction Score', row.get('Investment Score')),0)}</div>
      </div>
      <div class="mini-grid">
        <div class="mini-cell"><div class="mini-label">Kurs</div><div class="mini-value">{fmt_num(row.get('price'))}</div></div>
        <div class="mini-cell"><div class="mini-label">1 år</div><div class="mini-value">{fmt_pct(row.get('return_1y'))}</div></div>
        <div class="mini-cell"><div class="mini-label">Oppside</div><div class="mini-value">{row.get('Oppside','–')}</div></div>
        <div class="mini-cell"><div class="mini-label">Risiko</div><div class="mini-value">{fmt_num(row.get('Risk Score'),0)}/100</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_explanation(row):
    st.markdown("#### Investment Thesis")
    st.markdown(f"<div class='thesis'>{investment_thesis(row)}</div>", unsafe_allow_html=True)
    st.markdown("#### Hvorfor scorer aksjen slik?")
    for p in explain_score(row):
        st.markdown(f"<div class='positive'>✅ {p}</div>", unsafe_allow_html=True)
    flags = red_flag_engine(row)
    st.markdown("#### Røde flagg")
    if flags:
        for f in flags:
            st.markdown(f"<div class='redflag'>⚠️ {f}</div>", unsafe_allow_html=True)
    else:
        st.success("Ingen tydelige røde flagg fra den kvantitative modellen.")

# -----------------------------
# Error helper
# -----------------------------
def build_error_report(err="", context="Manuell feilrapport"):
    return f"""InvestAI feilrapport
Versjon: {APP_VERSION}
Tid: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Kontekst: {context}
Python: {sys.version.split()[0]}
Platform: {platform.platform()}
Streamlit: {st.__version__}
Pandas: {pd.__version__}
yfinance: {getattr(yf, '__version__', 'ukjent')}
Arbeidsmappe: {os.getcwd()}
Filer:
- {WATCHLIST_FILE}: {os.path.exists(WATCHLIST_FILE)}
- {OSLO_UNIVERSE_FILE}: {os.path.exists(OSLO_UNIVERSE_FILE)}
- {PORTFOLIO_FILE}: {os.path.exists(PORTFOLIO_FILE)}

Feil:
{err or 'Ingen feil limt inn.'}
"""

# -----------------------------
# Sidebar
# -----------------------------
ensure_csv_files()
universe = load_universe()

with st.sidebar:
    st.title("📈 InvestAI")
    st.caption("v11 Investment Intelligence · Gratisdata · Ikke finansiell rådgivning")
    mode = st.radio("Tema", ["Mørk", "Lys"], horizontal=True, index=0)
    apply_css(mode)
    st.divider()
    universe_mode = st.selectbox(
        "Univers",
        ["Kvalitet", "Oslo Børs", "Full Norge", "Rakettunivers"],
        index=1,
        help="Kvalitet = mer modne hovedlisteaksjer. Oslo Børs = hovedliste. Full Norge = alt i universfilen. Rakettunivers = Growth/small cap/tematiske kandidater først."
    )
    pre_universe = filter_universe_pre_screen(universe, universe_mode)
    all_sectors = sorted([s for s in pre_universe["sector"].dropna().unique() if str(s).strip()])
    sector_filter = st.multiselect("Sektorfilter", options=all_sectors, default=[])
    search = st.text_input("Søk ticker/selskap", "")
    max_default = min(100 if universe_mode != "Rakettunivers" else 140, int(len(pre_universe)))
    max_n = st.slider("Antall aksjer å screene", 10, int(len(pre_universe)), max_default, 10)
    st.caption(f"Valgt univers: {len(pre_universe)} av {len(universe)} tickere")
    st.divider()
    with st.expander("🛠 Feilhjelp / kopier feilmelding"):
        err = st.text_area("Lim inn feilmelding", height=130)
        report = build_error_report(err)
        components.html(copy_button_html(report, "📋 Kopier feilrapport"), height=75)
        st.download_button("Last ned feilrapport", report, file_name="investai_feilrapport.txt", mime="text/plain")

# apply_css after sidebar ensures global
apply_css(mode)

filtered_universe = pre_universe.copy()
if sector_filter:
    filtered_universe = filtered_universe[filtered_universe["sector"].isin(sector_filter)]
if search.strip():
    q = search.strip().lower()
    filtered_universe = filtered_universe[filtered_universe["ticker"].str.lower().str.contains(q) | filtered_universe["name"].str.lower().str.contains(q)]
if filtered_universe.empty:
    st.warning("Ingen aksjer matcher filteret. Viser hele universet i stedet.")
    filtered_universe = pre_universe.copy()

try:
    with st.spinner("Henter og scorer aksjer ..."):
        data = run_screen(filtered_universe, min(max_n, len(filtered_universe)))
except Exception:
    st.error("Screeningen feilet. Kopier feilrapporten under og send den hit.")
    st.code(build_error_report(traceback.format_exc(), "Screening"))
    st.stop()

if data.empty:
    st.error("Fant ingen data. Prøv færre tickere eller sjekk internettforbindelsen.")
    st.stop()

data_sorted = data.sort_values("Conviction Score" if "Conviction Score" in data.columns else "Investment Score", ascending=False).reset_index(drop=True)

# -----------------------------
# Header
# -----------------------------
st.markdown(f"""
<div class="topbar">
  <div class="topbar-title">InvestAI v11 · Investment Intelligence</div>
  <div class="subtle">Conviction Score, Red Flag Engine, Investment Thesis og Top Opportunities for Oslo Børs.</div>
</div>
""", unsafe_allow_html=True)

page = st.tabs(["🏠 Dashboard", "🎯 Top Opportunities", "🔎 Screener", "📌 Aksjeprofil", "🧭 Sektor & faktorer", "💼 Portefølje", "🧠 ChatGPT-flyt"])

# -----------------------------
# Dashboard
# -----------------------------
with page[0]:
    top = data_sorted.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Beste kandidat", f"{top['ticker']}", f"Conviction {fmt_num(top['Conviction Score'],0)}/100")
    with c2: kpi_card("Median conviction", f"{fmt_num(data['Conviction Score'].median(),0)}", f"{len(data)} aksjer · {universe_mode}")
    with c3: kpi_card("Topp rakett", data.sort_values("Rocket Score", ascending=False).iloc[0]["ticker"], f"Rocket {fmt_num(data['Rocket Score'].max(),0)}")
    with c4: kpi_card("Lavest risiko", data.sort_values("Risk Score", ascending=True).iloc[0]["ticker"], f"Risk {fmt_num(data['Risk Score'].min(),0)}")

    st.markdown("### Beslutningsoversikt")
    left, right = st.columns([1.1, 1])
    with left:
        dash_cols = ["ticker", "name", "sector", "Conviction", "Oppside", "price", "return_1y", "Conviction Score", "Rocket Score", "Risk Score"]
        show = data_sorted[dash_cols].head(10).rename(columns={
            "ticker":"Ticker", "name":"Selskap", "sector":"Sektor", "Conviction":"Conviction", "Oppside":"Oppside", "price":"Kurs", "return_1y":"1 år %",
        })
        st.dataframe(show, use_container_width=True, hide_index=True)
    with right:
        radar = data.dropna(subset=["Risk Score", "Rocket Score"]).copy()
        radar["market_cap_plot"] = radar["market_cap"].fillna(radar["market_cap"].median() if radar["market_cap"].notna().any() else 1e9)
        fig = px.scatter(radar, x="Risk Score", y="Rocket Score", size="market_cap_plot", color="sector", hover_name="ticker", template="plotly_dark" if mode=="Mørk" else "plotly_white", title="AI-radar: rakettpotensial vs risiko")
        fig.update_layout(height=420, margin=dict(l=10,r=10,t=50,b=10), legend_title_text="Sektor")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Kort oppsummering av toppkandidater")
    cols = st.columns(3)
    for i, (_, r) in enumerate(data_sorted.head(6).iterrows()):
        with cols[i % 3]:
            render_stock_card(r)

# -----------------------------
# Top Opportunities
# -----------------------------
with page[1]:
    st.markdown("### 🎯 Top Opportunities")
    st.caption("Beslutningssenteret rangerer aksjer etter Conviction Score og viser de mest interessante kandidatene på tvers av stil: kvalitet, rakett, verdi og momentum.")
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        kpi_card("Høyest conviction", data.sort_values("Conviction Score", ascending=False).iloc[0]["ticker"], f"{fmt_num(data['Conviction Score'].max(),0)}/100")
    with t2:
        kpi_card("Beste rakett", data.sort_values("Rocket Score", ascending=False).iloc[0]["ticker"], f"{fmt_num(data['Rocket Score'].max(),0)}/100")
    with t3:
        kpi_card("Beste verdi", data.sort_values("Value Score", ascending=False).iloc[0]["ticker"], f"{fmt_num(data['Value Score'].max(),0)}/100")
    with t4:
        safer = data[data["Risk Score"] <= 55]
        if safer.empty:
            safer = data
        kpi_card("Beste lavere risiko", safer.sort_values("Conviction Score", ascending=False).iloc[0]["ticker"], "Risk ≤ 55")

    tab_a, tab_b, tab_c, tab_d = st.tabs(["Høyest conviction", "Rakettkandidater", "Verdi", "Momentum"])
    opp_cols = ["ticker", "name", "sector", "Conviction", "Oppside", "Conviction Score", "Investment Score", "Rocket Score", "Value Score", "Momentum Score", "Risk Score", "Investment Thesis", "Red Flags"]
    rename_opp = {"ticker":"Ticker", "name":"Selskap", "sector":"Sektor", "Conviction Score":"Conviction Score", "Investment Score":"Investment Score", "Rocket Score":"Rakett", "Value Score":"Verdi", "Momentum Score":"Momentum", "Risk Score":"Risiko"}
    with tab_a:
        st.dataframe(data.sort_values("Conviction Score", ascending=False)[opp_cols].head(20).rename(columns=rename_opp), use_container_width=True, hide_index=True)
    with tab_b:
        st.dataframe(data.sort_values("Rocket Score", ascending=False)[opp_cols].head(20).rename(columns=rename_opp), use_container_width=True, hide_index=True)
    with tab_c:
        st.dataframe(data.sort_values("Value Score", ascending=False)[opp_cols].head(20).rename(columns=rename_opp), use_container_width=True, hide_index=True)
    with tab_d:
        st.dataframe(data.sort_values("Momentum Score", ascending=False)[opp_cols].head(20).rename(columns=rename_opp), use_container_width=True, hide_index=True)

    st.markdown("### Kortliste")
    cols_opp = st.columns(3)
    for i, (_, r) in enumerate(data.sort_values("Conviction Score", ascending=False).head(9).iterrows()):
        with cols_opp[i % 3]:
            render_stock_card(r)
            st.caption(investment_thesis(r))

# -----------------------------
# Screener
# -----------------------------
with page[2]:
    st.markdown("### Screener med færre og mer relevante kolonner")
    c1, c2, c3 = st.columns(3)
    min_score = c1.slider("Minimum Investment Score", 0, 100, 0, 5)
    max_risk = c2.slider("Maks Risk Score", 0, 100, 100, 5)
    sort_by = c3.selectbox("Sorter etter", ["Conviction Score", "Investment Score", "Rocket Score", "Momentum Score", "Value Score", "Quality Score", "Risk Score", "return_1y"])
    all_categories = sorted(set(",".join(data.get("Kategori", pd.Series(dtype=str)).fillna("").astype(str)).replace(" / ", "/").split(",")))
    all_categories = [x.strip() for x in all_categories if x.strip()]
    category_filter = st.multiselect("Kategori / tema", all_categories, default=[])
    view = data[(data["Investment Score"] >= min_score) & (data["Risk Score"] <= max_risk)].copy()
    if category_filter and "Kategori" in view.columns:
        view = view[view["Kategori"].astype(str).apply(lambda x: any(c in x for c in category_filter))]
    view = view.sort_values(sort_by, ascending=(sort_by=="Risk Score"))
    cols = ["ticker", "name", "sector", "Conviction", "Oppside", "Investment Thesis", "Red Flags", "price", "daily_return", "return_3m", "return_1y", "Conviction Score", "Investment Score", "Rocket Score", "Value Score", "Risk Score"]
    pretty = view[cols].rename(columns={
        "ticker":"Ticker", "name":"Selskap", "sector":"Sektor", "Conviction":"Conviction", "Oppside":"Oppside", "Investment Thesis":"Investment Thesis", "Red Flags":"Røde flagg", "price":"Kurs", "daily_return":"I dag %", "return_3m":"3 mnd %", "return_1y":"1 år %",
        "Conviction Score":"Conviction Score", "Investment Score":"Investeringsscore", "Rocket Score":"Rakettpotensial", "Value Score":"Verdsettelse", "Risk Score":"Risiko"
    })
    st.dataframe(pretty, use_container_width=True, hide_index=True)
    buffer = io.BytesIO()
    pretty.to_excel(buffer, index=False)
    st.download_button("⬇️ Last ned screener som Excel", buffer.getvalue(), file_name="investai_v11_screener.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -----------------------------
# Stock profile
# -----------------------------
with page[3]:
    st.markdown("### Aksjeprofil")
    tickers = data_sorted["ticker"].tolist()
    selected = st.selectbox("Velg aksje", tickers, index=0)
    row = data_sorted[data_sorted["ticker"] == selected].iloc[0]
    a, b = st.columns([0.95, 1.35])
    with a:
        render_stock_card(row)
        render_explanation(row)
    with b:
        hist = fetch_history(selected)
        if not hist.empty and "Close" in hist.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Close"], mode="lines", name="Kurs"))
            if len(hist) > 50:
                fig.add_trace(go.Scatter(x=hist["Date"], y=hist["Close"].rolling(50).mean(), mode="lines", name="50D snitt"))
            fig.update_layout(template="plotly_dark" if mode=="Mørk" else "plotly_white", title=f"{selected} · 1 års prishistorikk", height=430, margin=dict(l=10,r=10,t=45,b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ingen prishistorikk tilgjengelig fra gratis datakilde.")
        scores = pd.DataFrame({"Faktor":["Conviction","Momentum","Verdi","Kvalitet","Rakett","Lav risiko"], "Score":[row["Conviction Score"], row["Momentum Score"], row["Value Score"], row["Quality Score"], row["Rocket Score"], 100-row["Risk Score"]]})
        fig2 = px.bar(scores, x="Faktor", y="Score", range_y=[0,100], template="plotly_dark" if mode=="Mørk" else "plotly_white", title="Faktorprofil")
        fig2.update_layout(height=320, margin=dict(l=10,r=10,t=45,b=10))
        st.plotly_chart(fig2, use_container_width=True)
    scen = scenario_estimates(row)
    st.markdown("### Modellscenario")
    s1, s2, s3 = st.columns(3)
    with s1: kpi_card("Bear", fmt_num(scen["bear"]), "Ikke kursmål — enkel modell")
    with s2: kpi_card("Base", fmt_num(scen["base"]), "Ikke kursmål — enkel modell")
    with s3: kpi_card("Bull", fmt_num(scen["bull"]), "Ikke kursmål — enkel modell")

# -----------------------------
# Sector & factor view
# -----------------------------
with page[4]:
    st.markdown("### Sektor- og faktorvisning")
    sec = data.groupby("sector", dropna=False).agg(
        Antall=("ticker", "count"),
        Snittscore=("Investment Score", "mean"),
        Rakett=("Rocket Score", "mean"),
        Risiko=("Risk Score", "mean"),
        Momentum=("Momentum Score", "mean"),
    ).reset_index().sort_values("Snittscore", ascending=False)
    c1, c2 = st.columns([1,1])
    with c1:
        st.dataframe(sec.rename(columns={"sector":"Sektor"}), use_container_width=True, hide_index=True)
    with c2:
        fig = px.density_heatmap(data, x="sector", y="Investment Score", z="Rocket Score", histfunc="avg", template="plotly_dark" if mode=="Mørk" else "plotly_white", title="Sector heatmap")
        fig.update_layout(height=420, xaxis_tickangle=-35, margin=dict(l=10,r=10,t=50,b=90))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("### Kategorier og tema")
    if "Kategori" in data.columns:
        cat_rows = []
        for _, rr in data.iterrows():
            for cat in str(rr.get("Kategori", "")).split(","):
                cat = cat.strip()
                if cat:
                    cat_rows.append({"Kategori": cat, "Ticker": rr.get("ticker"), "Score": rr.get("Investment Score", 0)})
        cat_df = pd.DataFrame(cat_rows)
        if not cat_df.empty:
            cat_sum = cat_df.groupby("Kategori").agg(Antall=("Ticker", "count"), Snittscore=("Score", "mean")).reset_index().sort_values("Antall", ascending=False)
            st.dataframe(cat_sum, use_container_width=True, hide_index=True)

    st.markdown("### Risk matrix")
    fig = px.scatter(data, x="Risk Score", y="Investment Score", color="sector", size=data["market_cap"].fillna(1e9), hover_name="ticker", template="plotly_dark" if mode=="Mørk" else "plotly_white")
    fig.update_layout(height=480, margin=dict(l=10,r=10,t=35,b=10))
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Portfolio
# -----------------------------
with page[5]:
    st.markdown("### Porteføljetracker")
    try:
        port = pd.read_csv(PORTFOLIO_FILE)
    except Exception:
        port = pd.DataFrame(columns=["ticker", "shares", "cost_price", "note"])
    for col, default in {"ticker":"", "shares":0, "cost_price":0, "note":""}.items():
        if col not in port.columns:
            port[col] = default
    if port.empty or port["ticker"].astype(str).str.strip().eq("").all():
        st.info("Ingen portefølje registrert enda. Legg inn rader i portfolio.csv: ticker,shares,cost_price,note")
        st.code("ticker,shares,cost_price,note\nKOG.OL,10,850,Eksempel\nNOD.OL,25,120,Eksempel")
    else:
        port["ticker"] = port["ticker"].astype(str).str.upper().str.strip()
        merged = port.merge(data[["ticker", "price", "sector", "Conviction Score", "Investment Score", "Risk Score"]], on="ticker", how="left")
        merged["shares"] = pd.to_numeric(merged["shares"], errors="coerce").fillna(0)
        merged["cost_price"] = pd.to_numeric(merged["cost_price"], errors="coerce").fillna(0)
        merged["price"] = pd.to_numeric(merged["price"], errors="coerce").fillna(0)
        merged["market_value"] = merged["shares"] * merged["price"]
        merged["cost_value"] = merged["shares"] * merged["cost_price"]
        merged["pnl"] = merged["market_value"] - merged["cost_value"]
        p1,p2,p3 = st.columns(3)
        with p1: kpi_card("Markedsverdi", fmt_money(merged["market_value"].sum()), "Basert på tilgjengelig kurs")
        with p2: kpi_card("Gevinst/tap", fmt_money(merged["pnl"].sum()), "Urealisert")
        with p3: kpi_card("Antall posisjoner", str(len(merged)), "Fra portfolio.csv")
        st.dataframe(merged, use_container_width=True, hide_index=True)
        st.markdown("### Porteføljeanalyse")
        total_value = merged["market_value"].sum()
        if total_value > 0:
            merged["weight"] = merged["market_value"] / total_value * 100
            top_weight = merged["weight"].max()
            avg_conv = np.average(merged["Conviction Score"].fillna(50), weights=merged["market_value"].clip(lower=0)) if total_value > 0 else np.nan
            avg_risk = np.average(merged["Risk Score"].fillna(50), weights=merged["market_value"].clip(lower=0)) if total_value > 0 else np.nan
            p4, p5, p6 = st.columns(3)
            with p4: kpi_card("Vektet conviction", fmt_num(avg_conv,0), "Basert på screenede posisjoner")
            with p5: kpi_card("Vektet risiko", fmt_num(avg_risk,0), "Lavere er bedre")
            with p6: kpi_card("Største posisjon", fmt_pct(top_weight,1), "Konsentrasjon")
            if top_weight > 25:
                st.warning("Konsentrasjonsrisiko: én posisjon er over 25 % av porteføljen.")
            sec_exp = merged.groupby("sector", dropna=False)["market_value"].sum().reset_index()
            sec_exp["weight"] = sec_exp["market_value"] / total_value * 100
            if not sec_exp.empty:
                st.dataframe(sec_exp.rename(columns={"sector":"Sektor", "market_value":"Markedsverdi", "weight":"Vekt %"}), use_container_width=True, hide_index=True)
        if merged["market_value"].sum() > 0:
            fig = px.pie(merged, values="market_value", names="ticker", title="Porteføljevekter", template="plotly_dark" if mode=="Mørk" else "plotly_white")
            st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# ChatGPT flow
# -----------------------------
with page[6]:
    st.markdown("### Kopier komplett v11-analyse til ChatGPT")
    selected_prompt = st.selectbox("Velg aksje for analyseprompt", data_sorted["ticker"].tolist(), key="prompt_select")
    rowp = data_sorted[data_sorted["ticker"] == selected_prompt].iloc[0]
    prompt = make_prompt(rowp)
    components.html(copy_button_html(prompt, "📋 Kopier komplett analyseprompt"), height=75)
    st.text_area("Analyseprompt", value=prompt, height=420)
    st.download_button("⬇️ Last ned prompt", prompt, file_name=f"{selected_prompt}_chatgpt_prompt.txt", mime="text/plain")

st.caption("InvestAI er et hobby-/analyseverktøy. Data kan være mangelfull eller feil. Dette er ikke personlig finansiell rådgivning.")
