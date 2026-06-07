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
    page_title="InvestAI v9 Professional GUI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "InvestAI v9 Professional GUI"
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


def score_dataframe(df):
    df = df.copy()
    r1y = df["return_1y"].fillna(0)
    r3m = df["return_3m"].fillna(0)
    dly = df["daily_return"].fillna(0)
    vol = df["volatility"].fillna(df["volatility"].median() if df["volatility"].notna().any() else 45)
    dd = df["max_drawdown"].fillna(-40)
    pe = df["pe"].replace([np.inf, -np.inf], np.nan)
    ps = df["ps"].replace([np.inf, -np.inf], np.nan)
    debt = df["debt_to_equity"].replace([np.inf, -np.inf], np.nan)
    rev = df["revenue_growth"].fillna(0)
    margin = df["profit_margin"].fillna(0)

    df["Momentum Score"] = (50 + r1y * 0.35 + r3m * 0.65 + dly * 0.6).apply(clamp)
    value_pe = pe.apply(lambda x: 70 if pd.isna(x) else 90 if 0 < x < 12 else 75 if x < 20 else 55 if x < 35 else 35)
    value_ps = ps.apply(lambda x: 65 if pd.isna(x) else 90 if 0 < x < 1.5 else 75 if x < 3 else 55 if x < 6 else 35)
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

Data fra InvestAI v9:
- Sektor: {row.get('sector', 'Ukjent')}
- Marked: {row.get('market', 'Ukjent')}
- Siste kurs: {fmt_num(row.get('price'))}
- 1 års avkastning: {fmt_pct(row.get('return_1y'))}
- 3 mnd avkastning: {fmt_pct(row.get('return_3m'))}
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
    c = score_color(row.get("Investment Score", 0))
    st.markdown(f"""
    <div class="stock-card">
      <div class="stock-head">
        <div>
          <div class="ticker">{row.get('ticker','')}</div>
          <div class="company">{row.get('name','')} · {row.get('sector','Ukjent')}</div>
          <span class="pill">{status_label(row.get('Investment Score', 0))}</span>
          <span class="pill">Risiko: {risk_label(row.get('Risk Score', 0))}</span>
        </div>
        <div class="score-badge" style="background:{c};">{fmt_num(row.get('Investment Score'),0)}</div>
      </div>
      <div class="mini-grid">
        <div class="mini-cell"><div class="mini-label">Kurs</div><div class="mini-value">{fmt_num(row.get('price'))}</div></div>
        <div class="mini-cell"><div class="mini-label">1 år</div><div class="mini-value">{fmt_pct(row.get('return_1y'))}</div></div>
        <div class="mini-cell"><div class="mini-label">Rakett</div><div class="mini-value">{fmt_num(row.get('Rocket Score'),0)}/100</div></div>
        <div class="mini-cell"><div class="mini-label">Risiko</div><div class="mini-value">{fmt_num(row.get('Risk Score'),0)}/100</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_explanation(row):
    st.markdown("#### Hvorfor scorer aksjen slik?")
    for p in explain_score(row):
        st.markdown(f"<div class='positive'>✅ {p}</div>", unsafe_allow_html=True)
    flags = red_flags(row)
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
    st.caption("v9 Professional GUI · Gratisdata · Ikke finansiell rådgivning")
    mode = st.radio("Tema", ["Mørk", "Lys"], horizontal=True, index=0)
    apply_css(mode)
    st.divider()
    all_sectors = sorted([s for s in universe["sector"].dropna().unique() if str(s).strip()])
    sector_filter = st.multiselect("Sektorfilter", options=all_sectors, default=[])
    search = st.text_input("Søk ticker/selskap", "")
    max_n = st.slider("Antall aksjer å screene", 10, int(len(universe)), min(80, int(len(universe))), 10)
    st.caption(f"Univers: {len(universe)} tickere")
    st.divider()
    with st.expander("🛠 Feilhjelp / kopier feilmelding"):
        err = st.text_area("Lim inn feilmelding", height=130)
        report = build_error_report(err)
        components.html(copy_button_html(report, "📋 Kopier feilrapport"), height=75)
        st.download_button("Last ned feilrapport", report, file_name="investai_feilrapport.txt", mime="text/plain")

# apply_css after sidebar ensures global
apply_css(mode)

filtered_universe = universe.copy()
if sector_filter:
    filtered_universe = filtered_universe[filtered_universe["sector"].isin(sector_filter)]
if search.strip():
    q = search.strip().lower()
    filtered_universe = filtered_universe[filtered_universe["ticker"].str.lower().str.contains(q) | filtered_universe["name"].str.lower().str.contains(q)]
if filtered_universe.empty:
    st.warning("Ingen aksjer matcher filteret. Viser hele universet i stedet.")
    filtered_universe = universe.copy()

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

data_sorted = data.sort_values("Investment Score", ascending=False).reset_index(drop=True)

# -----------------------------
# Header
# -----------------------------
st.markdown(f"""
<div class="topbar">
  <div class="topbar-title">InvestAI v9 · Professional GUI</div>
  <div class="subtle">Renere dashboard, aksjeprofil, forklaringsmotor, red flags og bedre ChatGPT-flyt.</div>
</div>
""", unsafe_allow_html=True)

page = st.tabs(["🏠 Dashboard", "🔎 Screener", "📌 Aksjeprofil", "🧭 Sektor & faktorer", "💼 Portefølje", "🧠 ChatGPT-flyt"])

# -----------------------------
# Dashboard
# -----------------------------
with page[0]:
    top = data_sorted.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Beste kandidat", f"{top['ticker']}", f"Score {fmt_num(top['Investment Score'],0)}/100")
    with c2: kpi_card("Median score", f"{fmt_num(data['Investment Score'].median(),0)}", f"{len(data)} aksjer screenet")
    with c3: kpi_card("Topp rakett", data.sort_values("Rocket Score", ascending=False).iloc[0]["ticker"], f"Rocket {fmt_num(data['Rocket Score'].max(),0)}")
    with c4: kpi_card("Lavest risiko", data.sort_values("Risk Score", ascending=True).iloc[0]["ticker"], f"Risk {fmt_num(data['Risk Score'].min(),0)}")

    st.markdown("### Beslutningsoversikt")
    left, right = st.columns([1.1, 1])
    with left:
        dash_cols = ["ticker", "name", "sector", "price", "return_1y", "Investment Score", "Rocket Score", "Risk Score"]
        show = data_sorted[dash_cols].head(10).rename(columns={
            "ticker":"Ticker", "name":"Selskap", "sector":"Sektor", "price":"Kurs", "return_1y":"1 år %",
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
# Screener
# -----------------------------
with page[1]:
    st.markdown("### Screener med færre og mer relevante kolonner")
    c1, c2, c3 = st.columns(3)
    min_score = c1.slider("Minimum Investment Score", 0, 100, 0, 5)
    max_risk = c2.slider("Maks Risk Score", 0, 100, 100, 5)
    sort_by = c3.selectbox("Sorter etter", ["Investment Score", "Rocket Score", "Momentum Score", "Value Score", "Quality Score", "Risk Score", "return_1y"])
    view = data[(data["Investment Score"] >= min_score) & (data["Risk Score"] <= max_risk)].sort_values(sort_by, ascending=(sort_by=="Risk Score"))
    cols = ["ticker", "name", "sector", "price", "daily_return", "return_3m", "return_1y", "Investment Score", "Rocket Score", "Value Score", "Risk Score"]
    pretty = view[cols].rename(columns={
        "ticker":"Ticker", "name":"Selskap", "sector":"Sektor", "price":"Kurs", "daily_return":"I dag %", "return_3m":"3 mnd %", "return_1y":"1 år %",
        "Investment Score":"Investeringsscore", "Rocket Score":"Rakettpotensial", "Value Score":"Verdsettelse", "Risk Score":"Risiko"
    })
    st.dataframe(pretty, use_container_width=True, hide_index=True)
    buffer = io.BytesIO()
    pretty.to_excel(buffer, index=False)
    st.download_button("⬇️ Last ned screener som Excel", buffer.getvalue(), file_name="investai_v9_screener.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# -----------------------------
# Stock profile
# -----------------------------
with page[2]:
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
        scores = pd.DataFrame({"Faktor":["Momentum","Verdi","Kvalitet","Rakett","Lav risiko"], "Score":[row["Momentum Score"], row["Value Score"], row["Quality Score"], row["Rocket Score"], 100-row["Risk Score"]]})
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
with page[3]:
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
    st.markdown("### Risk matrix")
    fig = px.scatter(data, x="Risk Score", y="Investment Score", color="sector", size=data["market_cap"].fillna(1e9), hover_name="ticker", template="plotly_dark" if mode=="Mørk" else "plotly_white")
    fig.update_layout(height=480, margin=dict(l=10,r=10,t=35,b=10))
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Portfolio
# -----------------------------
with page[4]:
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
        merged = port.merge(data[["ticker", "price", "sector", "Investment Score", "Risk Score"]], on="ticker", how="left")
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
        if merged["market_value"].sum() > 0:
            fig = px.pie(merged, values="market_value", names="ticker", title="Porteføljevekter", template="plotly_dark" if mode=="Mørk" else "plotly_white")
            st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# ChatGPT flow
# -----------------------------
with page[5]:
    st.markdown("### Bedre kopier til ChatGPT-flyt")
    selected_prompt = st.selectbox("Velg aksje for analyseprompt", data_sorted["ticker"].tolist(), key="prompt_select")
    rowp = data_sorted[data_sorted["ticker"] == selected_prompt].iloc[0]
    prompt = make_prompt(rowp)
    components.html(copy_button_html(prompt, "📋 Kopier komplett analyseprompt"), height=75)
    st.text_area("Analyseprompt", value=prompt, height=420)
    st.download_button("⬇️ Last ned prompt", prompt, file_name=f"{selected_prompt}_chatgpt_prompt.txt", mime="text/plain")

st.caption("InvestAI er et hobby-/analyseverktøy. Data kan være mangelfull eller feil. Dette er ikke personlig finansiell rådgivning.")
