
import os
import io
import math
import sqlite3
import sys
import platform
import traceback
import json
from datetime import datetime, timedelta, date

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px




# =========================================================
# ERROR REPORTING / COPY HELPERS
# =========================================================
def build_error_report(error_text="", context="Manuell feilrapport"):
    """Lag en kopierbar feilrapport uten sensitive hemmeligheter."""
    try:
        py_ver = sys.version.split()[0]
    except Exception:
        py_ver = "ukjent"
    try:
        st_ver = st.__version__
    except Exception:
        st_ver = "ukjent"
    try:
        pd_ver = pd.__version__
    except Exception:
        pd_ver = "ukjent"
    try:
        yf_ver = yf.__version__
    except Exception:
        yf_ver = "ukjent"
    try:
        plotly_ver = go.__version__
    except Exception:
        try:
            import plotly
            plotly_ver = plotly.__version__
        except Exception:
            plotly_ver = "ukjent"

    files = []
    for fp in [WATCHLIST_FILE, PORTFOLIO_FILE, INSIDER_FILE, EARNINGS_FILE, NOTES_FILE, DB_FILE]:
        try:
            files.append(f"{fp}: {'finnes' if os.path.exists(fp) else 'mangler'}")
        except Exception:
            files.append(f"{fp}: ukjent")

    return f"""InvestAI feilrapport
Tidspunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Kontekst: {context}
Python: {py_ver}
Plattform: {platform.platform()}
Streamlit: {st_ver}
Pandas: {pd_ver}
yfinance: {yf_ver}
Plotly: {plotly_ver}
Arbeidsmappe: {os.getcwd()}
Filer: {', '.join(files)}

Feilmelding / traceback:
{str(error_text).strip() or 'Ingen feilmelding limt inn.'}
""".strip()


def copy_button_html(text, button_label="📋 Kopier feilrapport"):
    """Liten HTML/JS-knapp som kopierer tekst til utklippstavlen."""
    safe_text = json.dumps(text)
    safe_label = json.dumps(button_label)
    return f"""
    <div style="margin: 0.35rem 0 0.75rem 0;">
      <button id="copyErrBtn" style="
        width:100%; padding:0.65rem 0.8rem; border-radius:0.7rem;
        border:1px solid rgba(148,163,184,.45); background:#0f172a;
        color:#e5e7eb; font-weight:700; cursor:pointer;">
        {button_label}
      </button>
      <div id="copyErrStatus" style="font-size:0.78rem; color:#94a3b8; margin-top:0.35rem;"></div>
    </div>
    <script>
      const btn = document.getElementById('copyErrBtn');
      const status = document.getElementById('copyErrStatus');
      const txt = {safe_text};
      btn.innerText = {safe_label};
      btn.onclick = async () => {{
        try {{
          await navigator.clipboard.writeText(txt);
          status.innerText = 'Kopiert. Lim inn her i ChatGPT.';
        }} catch (e) {{
          status.innerText = 'Kunne ikke kopiere automatisk. Marker teksten under og kopier manuelt.';
        }}
      }};
    </script>
    """


def render_error_report_tool(location="sidebar"):
    """Vis et felt der brukeren kan lime inn Streamlit-feil og kopiere en ryddig rapport."""
    ui = st.sidebar if location == "sidebar" else st
    with ui.expander("🛠 Feilhjelp / kopier feilmelding", expanded=False):
        ui.caption("Lim inn feilen fra Streamlit her. Trykk kopier og send rapporten i ChatGPT.")
        err = ui.text_area("Feilmelding", height=160, placeholder="Lim inn Traceback / feilmelding her ...", key=f"error_text_{location}")
        report = build_error_report(err, context="Manuelt kopiert fra appen")
        components.html(copy_button_html(report), height=72)
        ui.download_button(
            "⬇️ Last ned feilrapport",
            data=report,
            file_name="investai_feilrapport.txt",
            mime="text/plain",
            key=f"download_error_report_{location}",
        )
        ui.code(report[:4000], language="text")


def render_exception_box(exc, context="Ukjent feil"):
    """Vis en pen feilboks med kopierbar rapport i stedet for hard crash."""
    tb = traceback.format_exc()
    report = build_error_report(tb, context=context)
    st.error(f"Det oppstod en feil i: {context}")
    with st.expander("Vis / kopier teknisk feilrapport", expanded=True):
        components.html(copy_button_html(report), height=72)
        st.download_button(
            "⬇️ Last ned feilrapport",
            data=report,
            file_name="investai_feilrapport.txt",
            mime="text/plain",
            key=f"download_exception_{abs(hash(report))}",
        )
        st.code(report, language="text")


def safe_render_stock_card(row, context="Aksjekort"):
    try:
        return render_stock_card(row)
    except Exception as exc:
        ticker = row.get("Ticker", row.get("ticker", "ukjent")) if hasattr(row, "get") else "ukjent"
        render_exception_box(exc, context=f"{context} · {ticker}")
        return ""


# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="InvestAI v8 Decision Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = "."  # Flat GitHub/Streamlit structure: datafiler ligger sammen med app.py
DB_FILE = "investai.db"
WATCHLIST_FILE = "watchlist.csv"
PORTFOLIO_FILE = "portfolio.csv"
INSIDER_FILE = "insider_watch.csv"
EARNINGS_FILE = "earnings_calendar.csv"
NOTES_FILE = "notes.csv"

DEFAULT_TICKERS = [
    # Oslo Børs large/mid/quality
    {"ticker": "EQNR.OL", "name": "Equinor", "sector": "Energi", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "DNB.OL", "name": "DNB", "sector": "Finans", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "KOG.OL", "name": "Kongsberg Gruppen", "sector": "Forsvar / Teknologi", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "MOWI.OL", "name": "Mowi", "sector": "Sjømat", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "SALM.OL", "name": "SalMar", "sector": "Sjømat", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "ORK.OL", "name": "Orkla", "sector": "Defensiv konsum", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "TEL.OL", "name": "Telenor", "sector": "Telekom", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "NHY.OL", "name": "Norsk Hydro", "sector": "Materialer", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "YAR.OL", "name": "Yara", "sector": "Gjødsel / Industri", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "AKRBP.OL", "name": "Aker BP", "sector": "Energi", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "SUBC.OL", "name": "Subsea 7", "sector": "Offshore", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "TOM.OL", "name": "Tomra", "sector": "Industri / Miljøteknologi", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "AUTO.OL", "name": "AutoStore", "sector": "Robotikk / Lagerautomasjon", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "NOD.OL", "name": "Nordic Semiconductor", "sector": "Semiconductor / IoT", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "KIT.OL", "name": "Kitron", "sector": "Industri / EMS", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "ATEA.OL", "name": "Atea", "sector": "IT-tjenester", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "BOUV.OL", "name": "Bouvet", "sector": "IT-konsulent", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "MEDI.OL", "name": "Medistim", "sector": "Medtech", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "PHO.OL", "name": "Photocure", "sector": "Medtech", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "HEX.OL", "name": "Hexagon Composites", "sector": "Energi / Hydrogen", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "AFG.OL", "name": "AF Gruppen", "sector": "Bygg / Infrastruktur", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "VEI.OL", "name": "Veidekke", "sector": "Bygg / Infrastruktur", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "SCHB.OL", "name": "Schibsted B", "sector": "Media / Marketplace", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "GJF.OL", "name": "Gjensidige Forsikring", "sector": "Forsikring", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "STB.OL", "name": "Storebrand", "sector": "Finans / Forsikring", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "ENTRA.OL", "name": "Entra", "sector": "Eiendom", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "BAKKA.OL", "name": "Bakkafrost", "sector": "Sjømat", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "LSG.OL", "name": "Lerøy Seafood", "sector": "Sjømat", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "WAWI.OL", "name": "Wallenius Wilhelmsen", "sector": "Shipping", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "MPCC.OL", "name": "MPC Container Ships", "sector": "Shipping", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "HAUTO.OL", "name": "Höegh Autoliners", "sector": "Shipping", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "BELCO.OL", "name": "Belships", "sector": "Shipping", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "ODF.OL", "name": "Odfjell A", "sector": "Shipping", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "ELK.OL", "name": "Elkem", "sector": "Materialer", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "SCATC.OL", "name": "Scatec", "sector": "Fornybar energi", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "BOR.OL", "name": "Borr Drilling", "sector": "Offshore drilling", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "SOFF.OL", "name": "Solstad Offshore", "sector": "Offshore", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "DOFG.OL", "name": "DOF Group", "sector": "Offshore", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "VAR.OL", "name": "Vår Energi", "sector": "Energi", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "NAS.OL", "name": "Norwegian Air Shuttle", "sector": "Luftfart", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "SATS.OL", "name": "SATS", "sector": "Konsum / Trening", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "XXL.OL", "name": "XXL", "sector": "Retail / Turnaround", "market": "Oslo Børs", "segment": "Hovedliste"},

    # Euronext Growth / small cap / high risk
    {"ticker": "AIRX.OL", "name": "Airthings", "sector": "IoT / Smart buildings", "market": "Oslo", "segment": "Euronext Growth"},
    {"ticker": "ZAP.OL", "name": "Zaptec", "sector": "EV-lading", "market": "Oslo", "segment": "Euronext Growth"},
    {"ticker": "NEL.OL", "name": "Nel", "sector": "Hydrogen", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "HPUR.OL", "name": "Hexagon Purus", "sector": "Hydrogen / Mobilitet", "market": "Oslo", "segment": "Euronext Growth"},
    {"ticker": "AGLX.OL", "name": "Agilyx", "sector": "Miljøteknologi", "market": "Oslo", "segment": "Euronext Growth"},
    {"ticker": "ACC.OL", "name": "Aker Carbon Capture", "sector": "CCS / Miljøteknologi", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "AKBM.OL", "name": "Aker BioMarine", "sector": "Biomarine", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "CLOUD.OL", "name": "Cloudberry Clean Energy", "sector": "Fornybar energi", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "HBC.OL", "name": "Hofseth BioCare", "sector": "Biotech / Biomarine", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "NEXT.OL", "name": "NEXT Biometrics", "sector": "Biometri / Teknologi", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "IDEX.OL", "name": "IDEX Biometrics", "sector": "Biometri / Teknologi", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "QFR.OL", "name": "Q-Free", "sector": "Transportteknologi", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "CRAYN.OL", "name": "Crayon", "sector": "Software / IT", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "TECH.OL", "name": "Techstep", "sector": "IT / Mobile", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "ARR.OL", "name": "Arribatec", "sector": "IT-konsulent", "market": "Oslo", "segment": "Euronext Growth"},
    {"ticker": "FRO.OL", "name": "Frontline", "sector": "Shipping / Tank", "market": "Oslo Børs", "segment": "Hovedliste"},
    {"ticker": "2020.OL", "name": "2020 Bulkers", "sector": "Shipping / Dry bulk", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "NOL.OL", "name": "Northern Ocean", "sector": "Offshore drilling", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "ARCH.OL", "name": "Archer", "sector": "Oil service", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "PEN.OL", "name": "Panoro Energy", "sector": "Energi / E&P", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "BWE.OL", "name": "BW Energy", "sector": "Energi / E&P", "market": "Oslo", "segment": "Hovedliste"},
    {"ticker": "QEC.OL", "name": "Questerre Energy", "sector": "Energi / Høy risiko", "market": "Oslo", "segment": "Hovedliste"},

    # Global comparison / AI
    {"ticker": "AAPL", "name": "Apple", "sector": "US Big Tech", "market": "USA", "segment": "USA"},
    {"ticker": "MSFT", "name": "Microsoft", "sector": "US Big Tech / AI", "market": "USA", "segment": "USA"},
    {"ticker": "NVDA", "name": "Nvidia", "sector": "AI / Semiconductor", "market": "USA", "segment": "USA"},
    {"ticker": "ASML", "name": "ASML", "sector": "Semiconductor Equipment", "market": "Europa", "segment": "Europa"},
]

FALLBACK_PRICES = {
    "KOG.OL": 930, "NOD.OL": 118, "KIT.OL": 43, "PHO.OL": 66, "AIRX.OL": 3.1,
    "ZAP.OL": 13.4, "HEX.OL": 22.1, "AKRBP.OL": 269, "SALM.OL": 612, "DNB.OL": 218,
    "EQNR.OL": 290, "TEL.OL": 130, "MOWI.OL": 190, "ORK.OL": 90, "TOM.OL": 135,
    "NHY.OL": 66, "YAR.OL": 335, "SUBC.OL": 185, "ATEA.OL": 145, "BOUV.OL": 65,
    "MEDI.OL": 260, "AUTO.OL": 13, "NEL.OL": 4.5, "HPUR.OL": 7.5,
    "AAPL": 190, "MSFT": 430, "NVDA": 120, "ASML": 900
}

STRATEGY_WEIGHTS = {
    "Balanced": {
        "quality": 0.22, "growth": 0.18, "value": 0.16, "momentum": 0.16,
        "technical": 0.12, "catalyst": 0.08, "risk_inverse": 0.08
    },
    "Rocket Hunter": {
        "quality": 0.08, "growth": 0.22, "value": 0.08, "momentum": 0.25,
        "technical": 0.20, "catalyst": 0.12, "risk_inverse": 0.05
    },
    "Compounder": {
        "quality": 0.32, "growth": 0.22, "value": 0.10, "momentum": 0.10,
        "technical": 0.08, "catalyst": 0.06, "risk_inverse": 0.12
    },
    "Value": {
        "quality": 0.18, "growth": 0.08, "value": 0.34, "momentum": 0.08,
        "technical": 0.08, "catalyst": 0.06, "risk_inverse": 0.18
    },
    "Defensive": {
        "quality": 0.28, "growth": 0.08, "value": 0.14, "momentum": 0.08,
        "technical": 0.07, "catalyst": 0.05, "risk_inverse": 0.30
    }
}


# =========================================================
# STYLE / MOBILE UI
# =========================================================
def inject_css():
    st.markdown("""
    <style>
    :root {
        --bg: #070b16;
        --panel: rgba(15, 23, 42, .76);
        --panel2: rgba(30, 41, 59, .62);
        --border: rgba(148, 163, 184, .18);
        --text: #e5e7eb;
        --muted: #94a3b8;
        --cyan: #22d3ee;
        --green: #22c55e;
        --red: #ef4444;
        --yellow: #f59e0b;
    }

    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 15% 0%, rgba(14,165,233,.18), transparent 34%),
            radial-gradient(circle at 85% 5%, rgba(34,197,94,.10), transparent 30%),
            linear-gradient(180deg, #070b16 0%, #0b1020 45%, #0a0f1d 100%);
    }

    .block-container {
        padding-top: .75rem;
        padding-bottom: 2rem;
        max-width: 1540px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15,23,42,.96), rgba(2,6,23,.98));
        border-right: 1px solid var(--border);
    }

    .hero-title {
        font-size: clamp(1.75rem, 4.8vw, 3.25rem);
        font-weight: 950;
        line-height: .95;
        letter-spacing: -.07em;
        background: linear-gradient(90deg, #e0f2fe, #22d3ee 40%, #86efac 90%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: .2rem 0 .15rem 0;
    }

    .hero-subtitle {
        color: var(--muted);
        font-size: clamp(.88rem, 2vw, 1.1rem);
        margin-bottom: .6rem;
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(15,23,42,.88), rgba(30,41,59,.55));
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 13px 14px;
        box-shadow: 0 16px 42px rgba(0,0,0,.20);
    }

    div[data-testid="stMetricValue"] {
        font-size: clamp(1.02rem, 2vw, 1.5rem);
        font-weight: 900;
        letter-spacing: -.035em;
    }

    div[data-testid="stMetricLabel"] {
        color: var(--muted);
        font-weight: 750;
        font-size: .82rem;
    }

    .terminal-card {
        border: 1px solid var(--border);
        background: linear-gradient(145deg, rgba(15,23,42,.82), rgba(30,41,59,.45));
        border-radius: 24px;
        padding: 16px 17px;
        box-shadow: 0 18px 55px rgba(0,0,0,.22);
        backdrop-filter: blur(12px);
        margin: 7px 0 14px 0;
    }

    .terminal-card h3 {
        margin: 0 0 4px 0;
        font-size: 1.02rem;
        letter-spacing: -.025em;
    }

    .subtle { color: var(--muted); font-size:0.9rem; }

    .pill {
        display:inline-block;
        padding:5px 10px;
        border-radius:999px;
        font-weight:850;
        font-size:0.76rem;
        margin:2px 4px 2px 0;
        border: 1px solid rgba(255,255,255,.08);
        white-space: nowrap;
    }

    .buy { background:rgba(34,197,94,.18); color:#bbf7d0; border-color:rgba(34,197,94,.35); }
    .hold { background:rgba(245,158,11,.18); color:#fde68a; border-color:rgba(245,158,11,.35); }
    .sell { background:rgba(239,68,68,.18); color:#fecaca; border-color:rgba(239,68,68,.35); }
    .risk-low { background:rgba(16,185,129,.18); color:#a7f3d0; border-color:rgba(16,185,129,.35); }
    .risk-med { background:rgba(245,158,11,.18); color:#fde68a; border-color:rgba(245,158,11,.35); }
    .risk-high { background:rgba(239,68,68,.18); color:#fecaca; border-color:rgba(239,68,68,.35); }
    .neutral { background:rgba(148,163,184,.14); color:#cbd5e1; }

    .scorebar {
        height: 8px;
        border-radius: 999px;
        background: rgba(148,163,184,.16);
        overflow: hidden;
        margin: 7px 0 9px 0;
    }
    .scorebar > div {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #38bdf8, #22c55e);
    }
    .riskbar > div { background: linear-gradient(90deg, #f59e0b, #ef4444); }

    .alert-card {
        border:1px solid rgba(56,189,248,.35);
        border-radius:18px;
        padding:11px 13px;
        margin:7px 0;
        background:linear-gradient(135deg, rgba(14,165,233,.13), rgba(15,23,42,.24));
    }

    .danger-card {
        border:1px solid rgba(239,68,68,.35);
        border-radius:18px;
        padding:11px 13px;
        margin:7px 0;
        background:rgba(239,68,68,.10);
    }

    .stock-card {
        border:1px solid var(--border);
        border-radius:24px;
        padding:15px 16px;
        margin:8px 0 12px 0;
        background:linear-gradient(145deg, rgba(15,23,42,.78), rgba(30,41,59,.44));
        box-shadow: 0 16px 45px rgba(0,0,0,.22);
    }

    .stock-card h3 {
        margin:0 0 3px 0;
        font-size: 1.08rem;
        letter-spacing: -.035em;
    }

    .stock-grid {
        display:grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 9px;
        margin: 10px 0 4px 0;
    }

    .mini-stat {
        background: rgba(2,6,23,.35);
        border: 1px solid rgba(148,163,184,.12);
        border-radius: 14px;
        padding: 8px 10px;
    }

    .mini-label { color: var(--muted); font-size: .68rem; font-weight: 800; text-transform: uppercase; letter-spacing:.06em; }
    .mini-value { font-size: .98rem; font-weight: 900; margin-top: 2px; }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 18px 45px rgba(0,0,0,.16);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 7px;
        overflow-x: auto;
        scrollbar-width: none;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }

    .stTabs [data-baseweb="tab"] {
        background: rgba(15,23,42,.65);
        border: 1px solid rgba(148,163,184,.16);
        border-radius: 999px;
        padding: 8px 12px;
        color: #cbd5e1;
        font-weight: 800;
        white-space: nowrap;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(34,211,238,.24), rgba(59,130,246,.22)) !important;
        border-color: rgba(34,211,238,.45) !important;
    }

    /* Mobile/desktop visibility */
    .mobile-only { display: none; }
    .desktop-only { display: block; }

    @media (max-width: 900px) {
        .block-container {
            padding-left: .55rem;
            padding-right: .55rem;
            padding-top: .35rem;
        }

        section[data-testid="stSidebar"] {
            width: min(92vw, 23rem) !important;
        }

        .hero-title {
            font-size: clamp(1.6rem, 8vw, 2.45rem);
            line-height: 1.02;
            letter-spacing: -.055em;
        }

        .hero-subtitle {
            font-size: .86rem;
        }

        div[data-testid="stMetric"] {
            padding: 9px 10px;
            border-radius: 16px;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.02rem;
        }

        div[data-testid="stMetricLabel"] {
            font-size: .72rem;
        }

        .stock-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .stock-card {
            border-radius: 20px;
            padding: 12px 12px;
        }
        .stock-card h3 { font-size: 1rem; }

        .terminal-card {
            border-radius: 20px;
            padding: 12px;
        }

        .pill {
            font-size: .68rem;
            padding: 4px 7px;
            margin-right: 2px;
        }

        div[data-testid="stDataFrame"] {
            font-size: .72rem;
        }

        .mobile-only { display: block; }
        .desktop-only { display: none; }

        .stTabs [data-baseweb="tab"] {
            padding: 7px 10px;
            font-size: .78rem;
        }
    }

    @media (max-width: 520px) {
        .stock-grid { grid-template-columns: 1fr 1fr; gap: 7px; }
        .mini-stat { padding: 7px 8px; }
        .mini-label { font-size: .62rem; }
        .mini-value { font-size: .9rem; }
        .subtle { font-size: .8rem; }
    }
    
    .dashboard-shell {
        display: grid;
        grid-template-columns: 1.15fr .85fr;
        gap: 14px;
        margin: 10px 0 14px 0;
    }
    .dash-panel {
        border: 1px solid var(--border);
        background: linear-gradient(145deg, rgba(15,23,42,.82), rgba(30,41,59,.44));
        border-radius: 24px;
        padding: 15px;
        box-shadow: 0 18px 48px rgba(0,0,0,.18);
        min-height: 100px;
    }
    .dash-panel h3 {
        margin: 0 0 9px 0;
        font-size: 1.03rem;
        letter-spacing: -.03em;
    }
    .market-tape {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 9px;
        margin: 10px 0 12px 0;
    }
    .tape-item {
        border: 1px solid rgba(148,163,184,.16);
        background: rgba(2,6,23,.32);
        border-radius: 16px;
        padding: 10px 11px;
    }
    .tape-label { color: var(--muted); font-size: .72rem; font-weight: 800; text-transform: uppercase; letter-spacing:.06em; }
    .tape-value { font-size: 1.05rem; font-weight: 950; margin-top: 2px; }
    .tape-change-pos { color:#86efac; font-weight: 900; }
    .tape-change-neg { color:#fca5a5; font-weight: 900; }
    .leader-row {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        padding: 9px 0;
        border-bottom: 1px solid rgba(148,163,184,.11);
    }
    .leader-row:last-child { border-bottom: 0; }
    .leader-name { font-weight: 900; letter-spacing: -.02em; }
    .leader-sub { color: var(--muted); font-size:.78rem; }
    .signal-chip {
        min-width: 58px;
        text-align:center;
        border-radius: 999px;
        padding: 4px 8px;
        font-size:.72rem;
        font-weight: 900;
    }
    .quad-grid {
        display:grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
    }
    .quad {
        border:1px solid rgba(148,163,184,.14);
        border-radius:16px;
        padding:10px;
        background:rgba(2,6,23,.28);
    }
    .quad-title { font-weight: 900; font-size: .82rem; margin-bottom:4px; }
    .quad-text { color: var(--muted); font-size:.78rem; }
    @media (max-width: 900px) {
        .dashboard-shell { grid-template-columns: 1fr; }
        .market-tape { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .quad-grid { grid-template-columns: 1fr; }
    }

    </style>
    """, unsafe_allow_html=True)


# =========================================================
# DATABASE
# =========================================================
def db_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS score_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TEXT NOT NULL,
        ticker TEXT NOT NULL,
        company TEXT,
        sector TEXT,
        market TEXT,
        strategy TEXT,
        investment_score REAL,
        strategy_score REAL,
        rocket_score REAL,
        risk_score REAL,
        momentum_score REAL,
        value_score REAL,
        quality_score REAL,
        technical_score REAL,
        catalyst_score REAL,
        signal TEXT,
        close_price REAL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cache_meta (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT
    )
    """)
    conn.commit()
    conn.close()


def save_score_history(df, strategy):
    if df is None or df.empty:
        return
    run_date = date.today().isoformat()
    out = pd.DataFrame({
        "run_date": run_date,
        "ticker": df["Ticker"],
        "company": df["Selskap"],
        "sector": df["Sektor"],
        "market": df["Marked"],
        "strategy": strategy,
        "investment_score": df["Investment Score"],
        "strategy_score": df["Strategy Score"],
        "rocket_score": df["Rocket Score"],
        "risk_score": df["Risk Score"],
        "momentum_score": df["Momentum Score"],
        "value_score": df["Value Score"],
        "quality_score": df["Quality Score"],
        "technical_score": df["Teknisk Score"],
        "catalyst_score": df["Catalyst Score"],
        "signal": df["Signal"],
        "close_price": df["Siste kurs"],
    })
    conn = db_conn()
    # replace today's rows for same strategy/tickers to avoid duplicates every refresh
    tickers = tuple(out["ticker"].unique().tolist())
    if tickers:
        placeholders = ",".join(["?"] * len(tickers))
        conn.execute(
            f"DELETE FROM score_history WHERE run_date=? AND strategy=? AND ticker IN ({placeholders})",
            (run_date, strategy, *tickers)
        )
    out.to_sql("score_history", conn, if_exists="append", index=False)
    conn.close()


def load_score_history(strategy=None):
    conn = db_conn()
    q = "SELECT * FROM score_history"
    params = []
    if strategy:
        q += " WHERE strategy=?"
        params.append(strategy)
    q += " ORDER BY run_date ASC"
    try:
        df = pd.read_sql_query(q, conn, params=params)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# =========================================================
# FILE SETUP
# =========================================================
def ensure_files():
    if not os.path.exists(WATCHLIST_FILE):
        pd.DataFrame(DEFAULT_TICKERS).to_csv(WATCHLIST_FILE, index=False)
    if not os.path.exists(PORTFOLIO_FILE):
        pd.DataFrame(columns=["ticker", "shares", "cost_price"]).to_csv(PORTFOLIO_FILE, index=False)
    if not os.path.exists(INSIDER_FILE):
        pd.DataFrame([
            {"ticker": "KOG.OL", "date": "2026-05-10", "person": "Eksempel insider", "type": "Kjøp", "value_nok": 250000, "comment": "Eksempeldata"},
            {"ticker": "PHO.OL", "date": "2026-05-11", "person": "Eksempel styremedlem", "type": "Kjøp", "value_nok": 90000, "comment": "Eksempeldata"},
            {"ticker": "NEL.OL", "date": "2026-05-12", "person": "Eksempel primærinnsider", "type": "Salg", "value_nok": 120000, "comment": "Eksempeldata"},
        ]).to_csv(INSIDER_FILE, index=False)
    if not os.path.exists(EARNINGS_FILE):
        today = date.today()
        pd.DataFrame([
            {"ticker": "KOG.OL", "company": "Kongsberg Gruppen", "report_date": str(today + timedelta(days=12)), "event": "Kvartalsrapport", "risk": "Moderat"},
            {"ticker": "NOD.OL", "company": "Nordic Semiconductor", "report_date": str(today + timedelta(days=18)), "event": "Kvartalsrapport", "risk": "Høy"},
            {"ticker": "DNB.OL", "company": "DNB", "report_date": str(today + timedelta(days=25)), "event": "Kvartalsrapport", "risk": "Lav"},
        ]).to_csv(EARNINGS_FILE, index=False)
    if not os.path.exists(NOTES_FILE):
        pd.DataFrame(columns=["ticker", "date", "note", "status"]).to_csv(NOTES_FILE, index=False)


# =========================================================
# UTILS
# =========================================================
def safe_float(x, default=0.0):
    try:
        if pd.isna(x) or x is None:
            return default
        return float(x)
    except Exception:
        return default


def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))



def scenario_estimates(row):
    """Simple scenario engine used by stock cards and decision intelligence.
    Returns expected upside/downside estimates in percent and a rough reward/risk ratio.
    Robust against missing/NaN values so Streamlit Cloud does not crash.
    """
    strategy = safe_float(row.get("Strategy Score", 50), 50)
    rocket = safe_float(row.get("Rocket Score", 50), 50)
    investment = safe_float(row.get("Investment Score", 50), 50)
    risk = safe_float(row.get("Risk Score", 50), 50)
    momentum = safe_float(row.get("Momentum Score", row.get("Teknisk Score", 50)), 50)
    value = safe_float(row.get("Value Score", 50), 50)

    # Upside estimate: higher for strong strategy/rocket/value/momentum, penalized by risk.
    base = (0.34 * strategy + 0.24 * investment + 0.22 * rocket + 0.10 * momentum + 0.10 * value) - 50
    base = clamp(base * 1.35, -25, 90)

    bull = base + 18 + max(0, rocket - 55) * 0.55 + max(0, momentum - 55) * 0.20
    bull = clamp(bull, 5, 180)

    bear = -10 - (risk * 0.55) + max(0, value - 60) * 0.08
    bear = clamp(bear, -85, -5)

    rr = abs(bull / bear) if bear != 0 else 0
    return {"bull": bull, "base": base, "bear": bear, "rr": rr}


def conviction_label(score):
    """Human-readable conviction label for card headers."""
    score = safe_float(score, 0)
    if score >= 80:
        return "Svært sterk kandidat"
    if score >= 68:
        return "Sterk kandidat"
    if score >= 55:
        return "Interessant å følge"
    if score >= 43:
        return "Nøytral / avvent"
    return "Svak kandidat"


def build_thesis(row):
    """Compact thesis text explaining the score in plain Norwegian."""
    parts = []
    if safe_float(row.get("Rocket Score", 0)) >= 70:
        parts.append("høyt rakettpotensial")
    if safe_float(row.get("Momentum Score", row.get("Teknisk Score", 0))) >= 65:
        parts.append("positiv markedstrend")
    if safe_float(row.get("Value Score", 0)) >= 65:
        parts.append("attraktiv verdsettelse")
    if safe_float(row.get("Quality Score", 0)) >= 65:
        parts.append("god kvalitet")
    if safe_float(row.get("Risk Score", 0)) >= 75:
        parts.append("men høy risiko")
    if safe_float(row.get("Risk Score", 100)) <= 40:
        parts.append("lavere risikoprofil")
    if not parts:
        signal = row.get("Signal", "HOLD")
        trend = row.get("Trend", "Blandet")
        parts.append(f"balansert case med signal {signal} og trend {trend}")
    return ", ".join(parts).capitalize() + "."



def positive_size_series(series, default=10):
    """Plotly marker sizes must be non-negative and non-null."""
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    if s.notna().any():
        fill = max(default, safe_float(s.abs().median(), default))
    else:
        fill = default
    s = s.abs().fillna(fill)
    return s.clip(lower=1)


def risk_label(score):
    if score < 40:
        return "Lav"
    if score < 70:
        return "Moderat"
    return "Høy"


def signal_label(score):
    if score >= 68:
        return "KJØP"
    if score >= 43:
        return "HOLD"
    return "SELG"


def style_signal(v):
    if v == "KJØP":
        return "background-color:#14532d;color:#dcfce7;font-weight:bold"
    if v == "HOLD":
        return "background-color:#713f12;color:#fef9c3;font-weight:bold"
    if v == "SELG":
        return "background-color:#7f1d1d;color:#fee2e2;font-weight:bold"
    return ""


def style_risk(v):
    if v == "Lav":
        return "background-color:#064e3b;color:#d1fae5;font-weight:bold"
    if v == "Moderat":
        return "background-color:#713f12;color:#fef9c3;font-weight:bold"
    if v == "Høy":
        return "background-color:#7f1d1d;color:#fee2e2;font-weight:bold"
    return ""


def load_csv_validated(path, required_defaults, aliases=None):
    aliases = aliases or {}
    try:
        df = pd.read_csv(path)
    except Exception:
        df = pd.DataFrame(columns=list(required_defaults.keys()))
    if df is None:
        df = pd.DataFrame(columns=list(required_defaults.keys()))
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={c: aliases.get(c, c) for c in df.columns})
    for col, default in required_defaults.items():
        if col not in df.columns:
            df[col] = default
    return df[list(required_defaults.keys())]


def load_insider():
    return load_csv_validated(
        INSIDER_FILE,
        {"ticker": "", "date": "", "person": "", "type": "", "value_nok": 0, "comment": ""},
        aliases={"aksje": "ticker", "dato": "date", "verdi": "value_nok", "kommentar": "comment"}
    )


def load_earnings():
    df = load_csv_validated(
        EARNINGS_FILE,
        {"ticker": "", "company": "", "report_date": "", "event": "", "risk": "Moderat"},
        aliases={"aksje": "ticker", "selskap": "company", "dato": "report_date", "hendelse": "event", "risiko": "risk"}
    )
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    return df


def load_notes():
    return load_csv_validated(NOTES_FILE, {"ticker": "", "date": "", "note": "", "status": "Åpen"})


def save_notes(df):
    df.to_csv(NOTES_FILE, index=False)


def load_portfolio():
    df = load_csv_validated(
        PORTFOLIO_FILE,
        {"ticker": "", "shares": 0.0, "cost_price": 0.0},
        aliases={"aksje": "ticker", "symbol": "ticker", "antall": "shares", "kjøpskurs": "cost_price", "kostpris": "cost_price"}
    )
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0)
    df["cost_price"] = pd.to_numeric(df["cost_price"], errors="coerce").fillna(0)
    df.to_csv(PORTFOLIO_FILE, index=False)
    return df


def save_portfolio(df):
    df[["ticker", "shares", "cost_price"]].to_csv(PORTFOLIO_FILE, index=False)


def render_stock_card(row):
    sig_class = "buy" if row["Signal"] == "KJØP" else "hold" if row["Signal"] == "HOLD" else "sell"
    risk_class = "risk-low" if row["Risiko"] == "Lav" else "risk-med" if row["Risiko"] == "Moderat" else "risk-high"
    trend_class = "buy" if row["Trend"] == "Positiv" else "hold" if row["Trend"] == "Blandet" else "sell"
    score = float(row["Strategy Score"])
    rocket = float(row["Rocket Score"])
    risk = float(row["Risk Score"])
    inv = float(row["Investment Score"])
    scenario = scenario_estimates(row)
    conviction = conviction_label(float(row["Strategy Score"]))
    thesis = build_thesis(row)
    return f"""
    <div class="stock-card">
        <h3>{row['Ticker']} · {row['Selskap']}</h3>
        <div class="subtle">{row['Sektor']} · {row['Marked']}</div>
        <div style="margin-top:8px;">
            <span class="pill {sig_class}">{row['Signal']}</span>
            <span class="pill {risk_class}">Risiko: {row['Risiko']} {risk:.0f}</span>
            <span class="pill {trend_class}">Trend: {row['Trend']}</span>
            <span class="pill neutral">RSI {float(row['RSI']):.0f}</span>
        </div>
        <div class="stock-grid">
            <div class="mini-stat"><div class="mini-label">Strategy</div><div class="mini-value">{score:.1f}</div><div class="scorebar"><div style="width:{max(0,min(100,score))}%"></div></div></div>
            <div class="mini-stat"><div class="mini-label">Rocket</div><div class="mini-value">{rocket:.1f}</div><div class="scorebar"><div style="width:{max(0,min(100,rocket))}%"></div></div></div>
            <div class="mini-stat"><div class="mini-label">Investment</div><div class="mini-value">{inv:.1f}</div><div class="scorebar"><div style="width:{max(0,min(100,inv))}%"></div></div></div>
            <div class="mini-stat"><div class="mini-label">Risk</div><div class="mini-value">{risk:.1f}</div><div class="scorebar riskbar"><div style="width:{max(0,min(100,risk))}%"></div></div></div>
        </div>
        <div class="subtle" style="margin-top:8px;"><b>{conviction}</b> · {thesis}</div>
        <div class="stock-grid" style="margin-top:10px;">
            <div class="mini-stat"><div class="mini-label">Bull</div><div class="mini-value">+{scenario["bull"]:.0f}%</div></div>
            <div class="mini-stat"><div class="mini-label">Base</div><div class="mini-value">+{scenario["base"]:.0f}%</div></div>
            <div class="mini-stat"><div class="mini-label">Bear</div><div class="mini-value">{scenario["bear"]:.0f}%</div></div>
            <div class="mini-stat"><div class="mini-label">R/R</div><div class="mini-value">{scenario["rr"]:.1f}x</div></div>
        </div>
        <div class="subtle" style="margin-top:8px;">{row['Forklaring']}</div>
    </div>
    """


# =========================================================
# CACHE / DATA FLOW
# =========================================================
@st.cache_data(ttl=1800, show_spinner=False)
def get_history(ticker, period="1y"):
    try:
        hist = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False, threads=False)
        if hist is None or hist.empty:
            raise ValueError("No data")
        hist = hist.reset_index()
        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = [c[0] if isinstance(c, tuple) else c for c in hist.columns]
        if "Date" not in hist.columns:
            hist = hist.rename(columns={hist.columns[0]: "Date"})
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col not in hist.columns:
                hist[col] = hist["Close"] if col != "Volume" and "Close" in hist.columns else 0
        return hist.dropna(subset=["Close"])
    except Exception:
        np.random.seed(abs(hash(ticker)) % (2**32))
        dates = pd.date_range(datetime.today() - timedelta(days=365), periods=252, freq="B")
        base = FALLBACK_PRICES.get(ticker, 100)
        returns = np.random.normal(0.0004, 0.024, len(dates))
        close = base * np.cumprod(1 + returns)
        open_ = close * (1 + np.random.normal(0, 0.006, len(dates)))
        high = np.maximum(open_, close) * (1 + np.random.uniform(0, 0.015, len(dates)))
        low = np.minimum(open_, close) * (1 - np.random.uniform(0, 0.015, len(dates)))
        volume = np.random.randint(20000, 900000, len(dates))
        return pd.DataFrame({"Date": dates, "Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume})


@st.cache_data(ttl=3600, show_spinner=False)
def get_info(ticker):
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def get_macro_assets():
    assets = {
        "S&P 500": "^GSPC",
        "Nasdaq": "^IXIC",
        "OSEBX proxy": "DNB.OL",
        "Olje Brent": "BZ=F",
        "USD/NOK": "NOK=X",
        "VIX": "^VIX",
        "Bitcoin": "BTC-USD",
    }
    rows = []
    for name, ticker in assets.items():
        hist = get_history(ticker, "6mo")
        if hist.empty:
            continue
        close = safe_float(hist["Close"].iloc[-1])
        start = safe_float(hist["Close"].iloc[0], close)
        ret = (close / start - 1) * 100 if start else 0
        one_m = hist.tail(22)
        ret_1m = (close / safe_float(one_m["Close"].iloc[0], close) - 1) * 100 if len(one_m) > 2 else 0
        rows.append({"Asset": name, "Ticker": ticker, "Siste": close, "6m %": ret, "1m %": ret_1m})
    return pd.DataFrame(rows)


# =========================================================
# INDICATORS / SCORING ENGINE
# =========================================================
def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def calculate_macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


def add_technical_indicators(hist):
    h = hist.copy()
    h["MA20"] = h["Close"].rolling(20).mean()
    h["MA50"] = h["Close"].rolling(50).mean()
    h["MA200"] = h["Close"].rolling(200).mean()
    h["RSI"] = calculate_rsi(h["Close"])
    h["MACD"], h["MACD_signal"], h["MACD_hist"] = calculate_macd(h["Close"])
    h["Volume_MA20"] = h["Volume"].rolling(20).mean()
    h["High_60"] = h["Close"].rolling(60).max()
    h["Low_60"] = h["Close"].rolling(60).min()
    return h


def technical_summary(hist):
    h = add_technical_indicators(hist)
    last = h.iloc[-1]
    close = safe_float(last["Close"])
    ma50 = safe_float(last["MA50"], close)
    ma200 = safe_float(last["MA200"], close)
    rsi = safe_float(last["RSI"], 50)
    macd = safe_float(last["MACD"], 0)
    macds = safe_float(last["MACD_signal"], 0)
    vol = safe_float(last["Volume"], 0)
    volma = safe_float(last["Volume_MA20"], vol if vol else 1)
    high60_prev = h["Close"].rolling(60).max().shift(1).iloc[-1]
    low60 = h["Low_60"].iloc[-1]

    trend_score = 50
    trend_score += 15 if close > ma50 else -15
    trend_score += 20 if close > ma200 else -20
    trend_score += 10 if ma50 > ma200 else -10

    if 45 <= rsi <= 65:
        rsi_score = 70
    elif 35 <= rsi < 45:
        rsi_score = 58
    elif 65 < rsi <= 75:
        rsi_score = 55
    elif rsi < 30:
        rsi_score = 40
    elif rsi > 80:
        rsi_score = 25
    else:
        rsi_score = 50

    macd_score = 65 if macd > macds else 38
    breakout = bool(close > safe_float(high60_prev, close * 2) and vol > 1.2 * safe_float(volma, vol))
    breakdown = bool(close < safe_float(low60, close / 2))
    volume_score = 70 if vol > 1.5 * safe_float(volma, vol) else 55 if vol > volma else 45

    technical_score = clamp(0.38 * trend_score + 0.22 * rsi_score + 0.22 * macd_score + 0.18 * volume_score)
    if breakout:
        technical_score = clamp(technical_score + 12)
    if breakdown:
        technical_score = clamp(technical_score - 20)

    return {
        "Teknisk Score": technical_score,
        "RSI": rsi,
        "MA50": ma50,
        "MA200": ma200,
        "MACD": macd,
        "MACD Signal": macds,
        "Volum Spike": vol > 1.5 * safe_float(volma, vol),
        "Breakout": breakout,
        "Breakdown": breakdown,
        "Trend": "Positiv" if close > ma50 and close > ma200 else "Blandet" if close > ma50 else "Negativ",
    }


def compute_market_regime(macro_df):
    if macro_df.empty:
        return "Nøytral", "Manglende makrodata", 50

    def asset_ret(name, col="1m %"):
        row = macro_df[macro_df["Asset"] == name]
        return safe_float(row[col].iloc[0], 0) if not row.empty else 0

    nasdaq_1m = asset_ret("Nasdaq")
    sp_1m = asset_ret("S&P 500")
    oil_1m = asset_ret("Olje Brent")
    vix = safe_float(macro_df.loc[macro_df["Asset"] == "VIX", "Siste"].iloc[0], 20) if not macro_df[macro_df["Asset"] == "VIX"].empty else 20

    risk_on_score = 50 + nasdaq_1m * 2.0 + sp_1m * 1.5 - max(0, vix - 18) * 1.2
    if oil_1m > 5:
        regime = "Energi / inflasjonspress"
        comment = "Olje styrker seg; energi og råvareeksponering kan favoriseres."
    elif risk_on_score >= 60:
        regime = "Risk-on / vekstvennlig"
        comment = "Momentum i brede indekser og moderat VIX favoriserer vekst og small caps."
    elif risk_on_score <= 40:
        regime = "Risk-off / defensivt"
        comment = "Svak indeksutvikling eller høy VIX favoriserer kvalitet, defensivt og lav risiko."
    else:
        regime = "Nøytral / selektiv"
        comment = "Ingen tydelig makroretning; aksjespesifikke triggere bør vektlegges."
    return regime, comment, clamp(risk_on_score)


def regime_sector_bias(regime):
    if "Energi" in regime:
        return {"Energi": 8, "Offshore": 7, "Materialer": 4, "US Big Tech": -2, "Hydrogen": -2}
    if "Risk-on" in regime:
        return {"US Big Tech": 6, "AI": 6, "Semiconductor": 5, "Hydrogen": 4, "Robotikk": 4, "Defensiv": -3}
    if "Risk-off" in regime:
        return {"Defensiv": 7, "Telekom": 5, "Finans": 2, "Hydrogen": -6, "Small": -5, "Robotikk": -4}
    return {}


def sector_bias_score(sector, regime):
    bias = regime_sector_bias(regime)
    score = 0
    for key, val in bias.items():
        if key.lower() in sector.lower():
            score += val
    return score


def score_stock(row, strategy, regime):
    ticker = row["ticker"]
    sector = row.get("sector", "Ukjent")
    hist = get_history(ticker)
    tech = technical_summary(hist)

    close = safe_float(hist["Close"].iloc[-1], FALLBACK_PRICES.get(ticker, 100))
    first = safe_float(hist["Close"].iloc[0], close)
    one_y = ((close / first) - 1) * 100 if first else 0
    recent_3m = hist.tail(63)
    three_m = ((close / safe_float(recent_3m["Close"].iloc[0], close)) - 1) * 100 if len(recent_3m) > 3 else 0
    vol = hist["Close"].pct_change().std() * math.sqrt(252) * 100
    dd = ((close / hist["Close"].cummax().iloc[-1]) - 1) * 100

    info = get_info(ticker)
    market_cap = safe_float(info.get("marketCap"), 0)
    trailing_pe = safe_float(info.get("trailingPE"), np.nan)
    ps = safe_float(info.get("priceToSalesTrailing12Months"), np.nan)
    debt_to_equity = safe_float(info.get("debtToEquity"), np.nan)
    revenue_growth = safe_float(info.get("revenueGrowth"), np.nan)
    profit_margin = safe_float(info.get("profitMargins"), np.nan)

    if np.isnan(trailing_pe) or trailing_pe <= 0:
        trailing_pe = 22 + (abs(hash(ticker)) % 20)
    if np.isnan(ps) or ps <= 0:
        ps = 1.5 + (abs(hash(ticker[::-1])) % 40) / 10
    if np.isnan(revenue_growth):
        revenue_growth = (abs(hash(ticker + "g")) % 45) / 100 - 0.05
    if np.isnan(profit_margin):
        profit_margin = (abs(hash(ticker + "m")) % 25) / 100 - 0.05
    if market_cap <= 0:
        market_cap = FALLBACK_PRICES.get(ticker, 100) * (10_000_000 + abs(hash(ticker)) % 900_000_000)
    if np.isnan(debt_to_equity):
        debt_to_equity = abs(hash(ticker + "d")) % 180

    earnings = load_earnings()
    upcoming = earnings[(earnings["ticker"].astype(str).str.upper() == ticker.upper()) & (earnings["report_date"].notna())]
    days_to_event = None
    event_risk_add = 0
    if not upcoming.empty:
        future = upcoming[upcoming["report_date"].dt.date >= date.today()]
        if not future.empty:
            nearest = future.sort_values("report_date").iloc[0]
            days_to_event = (nearest["report_date"].date() - date.today()).days
            event_risk_add = 7 if days_to_event <= 14 else 3 if days_to_event <= 30 else 0

    insider = load_insider()
    ticker_insider = insider[insider["ticker"].astype(str).str.upper() == ticker.upper()]
    insider_score = 50
    if not ticker_insider.empty:
        buy_value = pd.to_numeric(ticker_insider[ticker_insider["type"].astype(str).str.lower().str.contains("kjøp|buy", regex=True)]["value_nok"], errors="coerce").fillna(0).sum()
        sell_value = pd.to_numeric(ticker_insider[ticker_insider["type"].astype(str).str.lower().str.contains("salg|sell", regex=True)]["value_nok"], errors="coerce").fillna(0).sum()
        insider_score = clamp(50 + min(25, buy_value / 50000) - min(25, sell_value / 50000))

    momentum_score = clamp(50 + one_y * 0.45 + three_m * 0.65 + (tech["Teknisk Score"] - 50) * 0.4)
    value_score = clamp(85 - trailing_pe * 0.9 - ps * 3.0 + max(0, profit_margin * 100) * 0.7)
    growth_score = clamp(50 + revenue_growth * 120 + max(0, one_y) * 0.12)
    quality_score = clamp(45 + profit_margin * 160 - max(0, debt_to_equity - 80) * 0.16)
    risk_score = clamp(25 + vol * 0.55 + max(0, -dd) * 0.55 + max(0, debt_to_equity - 80) * 0.18 + event_risk_add)
    catalyst_score = clamp(50 + (12 if tech["Breakout"] else 0) + (8 if tech["Volum Spike"] else 0) + (insider_score - 50) * 0.6 + (6 if days_to_event is not None and days_to_event <= 30 else 0))
    macro_adj = sector_bias_score(sector, regime)

    rocket_score = clamp(
        0.25 * momentum_score +
        0.22 * growth_score +
        0.18 * tech["Teknisk Score"] +
        0.13 * catalyst_score +
        0.12 * value_score +
        0.10 * (100 - min(risk_score, 95)) +
        macro_adj
    )

    investment_score = clamp(
        0.23 * quality_score +
        0.20 * growth_score +
        0.17 * value_score +
        0.16 * momentum_score +
        0.12 * catalyst_score +
        0.12 * (100 - risk_score) +
        macro_adj * 0.65
    )

    weights = STRATEGY_WEIGHTS[strategy]
    strategy_score = clamp(
        weights["quality"] * quality_score +
        weights["growth"] * growth_score +
        weights["value"] * value_score +
        weights["momentum"] * momentum_score +
        weights["technical"] * tech["Teknisk Score"] +
        weights["catalyst"] * catalyst_score +
        weights["risk_inverse"] * (100 - risk_score) +
        macro_adj
    )

    signal_score = clamp(0.45 * strategy_score + 0.30 * investment_score + 0.15 * rocket_score + 0.10 * (100 - risk_score))
    signal = signal_label(signal_score)
    if risk_score > 82 and signal == "KJØP":
        signal = "HOLD"

    explanation = []
    if tech["Breakout"]:
        explanation.append("mulig teknisk breakout")
    if tech["Volum Spike"]:
        explanation.append("volumspike")
    if momentum_score > 70:
        explanation.append("sterkt momentum")
    if value_score > 70:
        explanation.append("attraktiv verdsettelse")
    if quality_score > 70:
        explanation.append("høy kvalitet")
    if insider_score > 60:
        explanation.append("positivt insider-signal")
    if macro_adj > 0:
        explanation.append("positiv makro-/sektorvind")
    if days_to_event is not None and days_to_event <= 30:
        explanation.append(f"kommende rapport om {days_to_event} dager")
    if risk_score > 70:
        explanation.append("høy risiko")
    if not explanation:
        explanation.append("blandet signalbilde")

    return {
        "Ticker": ticker,
        "Selskap": row.get("name", ticker),
        "Sektor": sector,
        "Marked": row.get("market", "Ukjent"),
        "Segment": row.get("segment", "Ukjent"),
        "Siste kurs": close,
        "Dagsendring %": hist["Close"].pct_change().iloc[-1] * 100 if len(hist) > 2 else 0,
        "1 år %": one_y,
        "3 mnd %": three_m,
        "Volatilitet %": vol,
        "Fall fra topp %": dd,
        "Markedsverdi": market_cap,
        "P/E": trailing_pe,
        "P/S": ps,
        "Omsetningsvekst %": revenue_growth * 100,
        "Netto margin %": profit_margin * 100,
        "Momentum Score": momentum_score,
        "Value Score": value_score,
        "Quality Score": quality_score,
        "Growth Score": growth_score,
        "Catalyst Score": catalyst_score,
        "Insider Score": insider_score,
        "Risk Score": risk_score,
        "Rocket Score": rocket_score,
        "Investment Score": investment_score,
        "Strategy Score": strategy_score,
        "Signal Score": signal_score,
        "Signal": signal,
        "Risiko": risk_label(risk_score),
        "Teknisk Score": tech["Teknisk Score"],
        "RSI": tech["RSI"],
        "Trend": tech["Trend"],
        "Breakout": tech["Breakout"],
        "Volum Spike": tech["Volum Spike"],
        "Dager til rapport": days_to_event if days_to_event is not None else "",
        "Makrojustering": macro_adj,
        "Forklaring": ", ".join(explanation),
    }





def explain_score(row):
    """Returnerer en enkel, kopierbar forklaring av hvorfor en aksje scorer slik den gjør.
    Robust mot manglende kolonner/NaN slik at appen ikke krasjer på Streamlit Cloud.
    """
    def sf(key, default=0.0):
        try:
            val = row.get(key, default)
            if pd.isna(val):
                return default
            return float(val)
        except Exception:
            return default

    def ss(key, default=""):
        try:
            val = row.get(key, default)
            if pd.isna(val):
                return default
            return str(val)
        except Exception:
            return default

    ticker = ss("Ticker", ss("ticker", "Ukjent"))
    company = ss("Selskap", ss("name", ticker))
    sector = ss("Sektor", ss("sector", "Ukjent sektor"))
    signal = ss("Signal", "HOLD")

    metrics = {
        "Strategi-score": sf("Strategy Score"),
        "Investment Score": sf("Investment Score"),
        "Rocket Score": sf("Rocket Score"),
        "Momentum Score": sf("Momentum Score"),
        "Value Score": sf("Value Score"),
        "Quality Score": sf("Quality Score"),
        "Growth Score": sf("Growth Score"),
        "Catalyst Score": sf("Catalyst Score"),
        "Risk Score": sf("Risk Score"),
        "Teknisk Score": sf("Teknisk Score"),
    }

    strengths = []
    risks = []

    if metrics["Momentum Score"] >= 70:
        strengths.append("sterkt kursmomentum")
    elif metrics["Momentum Score"] <= 35:
        risks.append("svakt momentum")

    if metrics["Value Score"] >= 70:
        strengths.append("attraktiv verdsettelse relativt til modellen")
    elif metrics["Value Score"] <= 35:
        risks.append("krevende verdsettelse")

    if metrics["Quality Score"] >= 70:
        strengths.append("høy kvalitet / lønnsomhet")
    elif metrics["Quality Score"] <= 35:
        risks.append("svak kvalitet eller presset lønnsomhet")

    if metrics["Growth Score"] >= 70:
        strengths.append("sterk vekstprofil")
    elif metrics["Growth Score"] <= 35:
        risks.append("svak vekstprofil")

    if metrics["Catalyst Score"] >= 70:
        strengths.append("tydelige katalysatorer")

    if metrics["Risk Score"] >= 70:
        risks.append("høyt risikonivå")
    elif metrics["Risk Score"] <= 35:
        strengths.append("relativt lav modellert risiko")

    if bool(row.get("Breakout", False)):
        strengths.append("mulig teknisk breakout")
    if bool(row.get("Volum Spike", False)):
        strengths.append("uvanlig volum / økt markedsinteresse")

    forklaring = ss("Forklaring", "")
    if forklaring:
        strengths.append(forklaring)

    strengths_txt = "\n".join([f"- {x}" for x in strengths[:7]]) or "- Ingen tydelige styrker fra modellen akkurat nå."
    risks_txt = "\n".join([f"- {x}" for x in risks[:7]]) or "- Ingen store røde flagg fra modellen, men sjekk alltid gjeld, kontantstrøm og nyheter manuelt."

    return f"""{ticker} – {company}
Sektor: {sector}
Signal: {signal}

Hovedscore:
- Strategi-score: {metrics['Strategi-score']:.0f}/100
- Investment Score: {metrics['Investment Score']:.0f}/100
- Rocket Score: {metrics['Rocket Score']:.0f}/100
- Risk Score: {metrics['Risk Score']:.0f}/100

Delkomponenter:
- Momentum: {metrics['Momentum Score']:.0f}/100
- Verdi: {metrics['Value Score']:.0f}/100
- Kvalitet: {metrics['Quality Score']:.0f}/100
- Vekst: {metrics['Growth Score']:.0f}/100
- Katalysatorer: {metrics['Catalyst Score']:.0f}/100
- Teknisk: {metrics['Teknisk Score']:.0f}/100

Hvorfor aksjen scorer bra/svakt:
{strengths_txt}

Viktigste risikoer / sjekkpunkter:
{risks_txt}

Merk: Dette er en kvantitativ screeningmodell, ikke en kjøpsanbefaling. Bruk den som startpunkt for videre analyse.
"""

def signal_class(sig):
    return "buy" if sig == "KJØP" else "hold" if sig == "HOLD" else "sell"

def compact_leaderboard(df, title_col="Ticker", score_col="Strategy Score", n=5):
    rows = []
    for _, r in df.head(n).iterrows():
        sig = r.get("Signal", "HOLD")
        cls = signal_class(sig)
        rows.append(f"""
        <div class="leader-row">
            <div>
                <div class="leader-name">{r.get(title_col, r.get('Ticker',''))}</div>
                <div class="leader-sub">{r.get('Selskap','')} · {r.get('Sektor','')}</div>
            </div>
            <div style="text-align:right;">
                <div class="signal-chip {cls}">{sig}</div>
                <div class="leader-sub">{float(r.get(score_col, 0)):.1f}</div>
            </div>
        </div>
        """)
    return "".join(rows)

def render_market_tape(macro_df):
    if macro_df is None or macro_df.empty:
        return '<div class="subtle">Ingen markedsdata tilgjengelig.</div>'
    preferred = ["S&P 500", "Nasdaq", "Olje Brent", "VIX", "USD/NOK", "Bitcoin"]
    m = macro_df[macro_df["Asset"].isin(preferred)].head(6)
    items = []
    for _, r in m.iterrows():
        ch = float(r.get("1m %", 0))
        cls = "tape-change-pos" if ch >= 0 else "tape-change-neg"
        items.append(f"""
        <div class="tape-item">
            <div class="tape-label">{r.get('Asset','')}</div>
            <div class="tape-value">{float(r.get('Siste',0)):.2f}</div>
            <div class="{cls}">{ch:+.1f}% 1m</div>
        </div>
        """)
    return '<div class="market-tape">' + "".join(items) + '</div>'

def render_dashboard_summary(data, regime, regime_comment, risk_on_score, macro_df):
    buy_count = int((data["Signal"] == "KJØP").sum())
    hold_count = int((data["Signal"] == "HOLD").sum())
    sell_count = int((data["Signal"] == "SELG").sum())
    high_risk = int((data["Risk Score"] >= 70).sum())
    avg_score = float(data["Strategy Score"].mean())
    return f"""
    <div class="dashboard-shell">
        <div class="dash-panel">
            <h3>🌍 Markedspuls</h3>
            <div class="subtle">{regime} · Risk-on {risk_on_score:.0f}/100</div>
            <p class="subtle" style="margin-top:7px;">{regime_comment}</p>
            {render_market_tape(macro_df)}
        </div>
        <div class="dash-panel">
            <h3>📌 Screeningstatus</h3>
            <div class="quad-grid">
                <div class="quad"><div class="quad-title">Kjøp-signaler</div><div class="tape-value">{buy_count}</div><div class="quad-text">Modellbasert, risikojustert</div></div>
                <div class="quad"><div class="quad-title">Hold</div><div class="tape-value">{hold_count}</div><div class="quad-text">Nøytral/avventende</div></div>
                <div class="quad"><div class="quad-title">Selg</div><div class="tape-value">{sell_count}</div><div class="quad-text">Svakt signalbilde</div></div>
                <div class="quad"><div class="quad-title">Høy risiko</div><div class="tape-value">{high_risk}</div><div class="quad-text">Risk Score ≥ 70</div></div>
            </div>
            <div class="subtle" style="margin-top:10px;">Snitt Strategy Score: <b>{avg_score:.1f}</b></div>
        </div>
    </div>
    """


# =========================================================
# CHARTS
# =========================================================
def plot_candlestick(ticker, template):
    hist = add_technical_indicators(get_history(ticker))
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist["Date"], open=hist["Open"], high=hist["High"], low=hist["Low"], close=hist["Close"], name="Kurs"))
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist["MA50"], mode="lines", name="MA50"))
    fig.add_trace(go.Scatter(x=hist["Date"], y=hist["MA200"], mode="lines", name="MA200"))
    fig.update_layout(template=template, height=460, margin=dict(l=20, r=20, t=40, b=20), xaxis_rangeslider_visible=False, title=f"{ticker} - teknisk graf")
    return fig


def plot_score_history(ticker, strategy, template):
    hist = load_score_history(strategy)
    if hist.empty:
        return None
    h = hist[hist["ticker"] == ticker].copy()
    if h.empty:
        return None
    fig = go.Figure()
    for col, name in [
        ("strategy_score", "Strategy"),
        ("investment_score", "Investment"),
        ("rocket_score", "Rocket"),
        ("risk_score", "Risk"),
    ]:
        fig.add_trace(go.Scatter(x=h["run_date"], y=h[col], mode="lines+markers", name=name))
    fig.update_layout(template=template, height=360, margin=dict(l=20, r=20, t=40, b=20), title=f"Scorehistorikk: {ticker}")
    return fig


def make_prompt(row, regime, daily_brief):
    return f"""Analyser {row['Selskap']} ({row['Ticker']}) som investeringscase på norsk.

Bruk en profesjonell equity research-struktur.

Data fra InvestAI v7.1:
- Sektor: {row['Sektor']}
- Marked: {row['Marked']}
- Siste kurs: {row['Siste kurs']:.2f}
- 1 års avkastning: {row['1 år %']:.1f}%
- 3 mnd avkastning: {row['3 mnd %']:.1f}%
- Strategy Score: {row['Strategy Score']:.1f}/100
- Investment Score: {row['Investment Score']:.1f}/100
- Rocket Score: {row['Rocket Score']:.1f}/100
- Momentum Score: {row['Momentum Score']:.1f}/100
- Value Score: {row['Value Score']:.1f}/100
- Quality Score: {row['Quality Score']:.1f}/100
- Catalyst Score: {row['Catalyst Score']:.1f}/100
- Risk Score: {row['Risk Score']:.1f}/100
- Teknisk Score: {row['Teknisk Score']:.1f}/100
- RSI: {row['RSI']:.1f}
- Trend: {row['Trend']}
- Breakout: {row['Breakout']}
- Volum spike: {row['Volum Spike']}
- Modellbasert signal: {row['Signal']}
- Forklaring: {row['Forklaring']}
- Market regime: {regime}

Daily brief:
{daily_brief}

Vurder:
1. Kort investment case
2. Bull case
3. Bear case
4. Fundamental kvalitet
5. Teknisk bilde
6. Makro-/sektorbildet
7. Verdsettelse relativt til vekst og risiko
8. Risiko og røde flagg
9. Scenarioanalyse: bear/base/bull
10. Konklusjon

Viktig: Skill mellom fakta, estimater og egne vurderinger. Dette er ikke personlig finansiell rådgivning."""


# =========================================================
# APP START
# =========================================================
ensure_files()
init_db()

st.sidebar.title("📈 InvestAI v8")
st.sidebar.caption("SQLite, scorehistorikk, market regime, porteføljerisiko og conviction picks.")
render_error_report_tool("sidebar")

theme = st.sidebar.radio("Tema", ["Mørk", "Lys"], index=0)
plotly_template = "plotly_dark" if theme == "Mørk" else "plotly_white"

strategy = st.sidebar.selectbox("Strategi / scoremotor", list(STRATEGY_WEIGHTS.keys()), index=0)

watchlist_all = pd.read_csv(WATCHLIST_FILE)
# Backward-compatible CSV validation
for col, default in {"ticker": "", "name": "", "sector": "Ukjent", "market": "Ukjent", "segment": "Ukjent"}.items():
    if col not in watchlist_all.columns:
        watchlist_all[col] = default
watchlist_all["ticker"] = watchlist_all["ticker"].astype(str).str.upper().str.strip()

st.sidebar.markdown("---")
st.sidebar.subheader("Screening")
universe_mode = st.sidebar.selectbox(
    "Univers",
    ["Alle i watchlist", "Kun Oslo Børs / Oslo", "Kun hovedliste", "Kun Euronext Growth", "Kun globale sammenligninger"],
    index=1,
)
markets = st.sidebar.multiselect("Marked", sorted(watchlist_all["market"].dropna().unique()), default=[])
segments = st.sidebar.multiselect("Segment", sorted(watchlist_all["segment"].dropna().unique()), default=[])
sectors = st.sidebar.multiselect("Sektor", sorted(watchlist_all["sector"].dropna().unique()), default=[])
rocket_only = st.sidebar.checkbox("Rakettmodus: small/high-risk univers", value=False)
batch_warning = st.sidebar.checkbox("Jeg forstår at mange aksjer kan ta tid på gratisdata", value=True)

filtered = watchlist_all.copy()
if universe_mode == "Kun Oslo Børs / Oslo":
    filtered = filtered[filtered["market"].astype(str).str.contains("Oslo", case=False, na=False)]
elif universe_mode == "Kun hovedliste":
    filtered = filtered[filtered["segment"].astype(str).str.contains("Hovedliste", case=False, na=False)]
elif universe_mode == "Kun Euronext Growth":
    filtered = filtered[filtered["segment"].astype(str).str.contains("Growth", case=False, na=False)]
elif universe_mode == "Kun globale sammenligninger":
    filtered = filtered[~filtered["market"].astype(str).str.contains("Oslo", case=False, na=False)]

if markets:
    filtered = filtered[filtered["market"].isin(markets)]
if segments:
    filtered = filtered[filtered["segment"].isin(segments)]
if sectors:
    filtered = filtered[filtered["sector"].isin(sectors)]
if rocket_only:
    rocket_terms = "Hydrogen|Biotech|Biometri|Turnaround|Miljøteknologi|EV|IoT|Robotikk|Høy risiko|Euronext Growth|Small"
    filtered = filtered[
        filtered["sector"].astype(str).str.contains(rocket_terms, case=False, na=False) |
        filtered["segment"].astype(str).str.contains("Growth", case=False, na=False)
    ]

default_n = min(35, len(filtered)) if len(filtered) else 0
max_allowed = min(75, len(filtered)) if len(filtered) else 1
max_tickers = st.sidebar.slider("Antall aksjer å screene", 1, max_allowed, max(1, default_n))
filtered = filtered.head(max_tickers)

st.sidebar.caption(f"Univers etter filtre: {len(filtered)} aksjer. Full Oslo-liste her er utvidet, men ikke garantert komplett/offisiell.")

if st.sidebar.button("Tøm Streamlit-cache"):
    st.cache_data.clear()
    st.sidebar.success("Cache tømt.")

st.sidebar.caption("Signalene er modellbaserte og ikke personlig investeringsråd.")

st.markdown('<div class="hero-title">InvestAI v8 Decision Intelligence</div><div class="hero-subtitle">Beslutningsstøtte med thesis engine, bull/base/bear-scenarier og actionable insights</div>', unsafe_allow_html=True)
st.caption("v7.3 utvider universet betydelig. Merk: tickerlisten er en praktisk gratisliste, ikke en offisiell komplett Euronext-master.")

macro_df = get_macro_assets()
regime, regime_comment, risk_on_score = compute_market_regime(macro_df)

with st.spinner("Henter data via cache, beregner scoremotor og oppdaterer SQLite-historikk..."):
    rows = []
    for _, r in filtered.iterrows():
        try:
            rows.append(score_stock(r, strategy, regime))
        except Exception as e:
            st.warning(f"Klarte ikke analysere {r.get('ticker')}: {e}")
    data = pd.DataFrame(rows)

if data.empty:
    st.error("Ingen data tilgjengelig.")
    st.stop()

data = data.sort_values("Strategy Score", ascending=False)
save_score_history(data, strategy)

# Daily brief and alerts
top = data.iloc[0]
sector_perf = data.groupby("Sektor", as_index=False).agg({"3 mnd %": "mean", "Strategy Score": "mean", "Risk Score": "mean"}).sort_values("3 mnd %", ascending=False)
best_sector = sector_perf.iloc[0]["Sektor"] if not sector_perf.empty else "N/A"
weak_sector = sector_perf.iloc[-1]["Sektor"] if not sector_perf.empty else "N/A"

alerts = []
for _, r in data.iterrows():
    if r["Breakout"]:
        alerts.append(f"🚀 {r['Ticker']}: mulig breakout.")
    if r["Volum Spike"]:
        alerts.append(f"📊 {r['Ticker']}: volumspike.")
    if r["Risk Score"] > 80:
        alerts.append(f"⚠️ {r['Ticker']}: svært høy risiko.")
    if isinstance(r["Dager til rapport"], (int, float)) and r["Dager til rapport"] != "" and r["Dager til rapport"] <= 14:
        alerts.append(f"🗓 {r['Ticker']}: rapport innen {int(r['Dager til rapport'])} dager.")

daily_brief = (
    f"Market regime: {regime}. {regime_comment}\n"
    f"Risk-on score: {risk_on_score:.1f}/100.\n"
    f"Sterkeste sektor i screeningen: {best_sector}. Svakeste sektor: {weak_sector}.\n"
    f"Top conviction akkurat nå: {top['Ticker']} ({top['Selskap']}) med Strategy Score {top['Strategy Score']:.1f} og signal {top['Signal']}."
)

chart_config = {"displayModeBar": False, "responsive": True}
compact_cols = ["Ticker", "Signal", "Strategy Score", "Rocket Score", "Risk Score", "Risiko", "Trend", "Forklaring"]

# KPIs
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Screenet", len(data))
c2.metric("Strategi", strategy)
c3.metric("Kjøp", int((data["Signal"] == "KJØP").sum()))
c4.metric("Breakouts", int(data["Breakout"].sum()))
c5.metric("Risk-on", f"{risk_on_score:.0f}/100")
c6.metric("Top pick", top["Ticker"])

with st.expander("🗞 Daily Market Brief", expanded=True):
    st.markdown(daily_brief.replace("\n", "  \n"))
    if alerts:
        st.markdown("**Alerts:**")
        for a in alerts[:12]:
            st.markdown(f'<div class="alert-card">{a}</div>', unsafe_allow_html=True)

tabs = st.tabs([
    "🏠 Dashboard",
    "🏆 Conviction Picks",
    "📈 Historiske scores",
    "🌍 Market regime",
    "🔄 Sektorrotasjon",
    "📊 Teknisk",
    "⚠️ Risiko",
    "💼 Porteføljerisiko",
    "📝 Notater",
    "🧠 Prompt",
    "📤 Eksport",
])

show_cols = [
    "Ticker", "Selskap", "Sektor", "Marked", "Segment", "Siste kurs", "Dagsendring %", "1 år %",
    "Signal", "Strategy Score", "Investment Score", "Rocket Score", "Momentum Score",
    "Value Score", "Quality Score", "Teknisk Score", "Risk Score", "Risiko", "Trend",
    "Breakout", "Forklaring"
]

def formatted(df):
    styler = df.style
    if "Signal" in df.columns:
        styler = styler.map(style_signal, subset=["Signal"])
    if "Risiko" in df.columns:
        styler = styler.map(style_risk, subset=["Risiko"])

    formats = {
        "Siste kurs": "{:.2f}",
        "Dagsendring %": "{:+.1f}%",
        "1 år %": "{:+.1f}%",
        "Strategy Score": "{:.1f}",
        "Investment Score": "{:.1f}",
        "Rocket Score": "{:.1f}",
        "Momentum Score": "{:.1f}",
        "Value Score": "{:.1f}",
        "Quality Score": "{:.1f}",
        "Teknisk Score": "{:.1f}",
        "Risk Score": "{:.1f}",
    }
    formats = {k: v for k, v in formats.items() if k in df.columns}
    return styler.format(formats)

with tabs[0]:
    st.subheader("Dashboard")

    # Native Streamlit dashboard header: avoids raw HTML rendering issues on Streamlit Cloud/mobile.
    st.markdown("### 🌍 Markedspuls")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Market regime", regime)
    m2.metric("Risk-on score", f"{risk_on_score:.0f}/100")
    m3.metric("Sterkeste sektor", best_sector)
    m4.metric("Top pick", top["Ticker"])
    st.caption(regime_comment)

    if macro_df is not None and not macro_df.empty:
        tape_assets = ["S&P 500", "Nasdaq", "Olje Brent", "VIX", "USD/NOK", "Bitcoin"]
        tape = macro_df[macro_df["Asset"].isin(tape_assets)].head(6)
        tape_cols = st.columns(min(6, max(1, len(tape))))
        for i, (_, r) in enumerate(tape.iterrows()):
            with tape_cols[i % len(tape_cols)]:
                st.metric(
                    r["Asset"],
                    f"{float(r['Siste']):.2f}",
                    f"{float(r['1m %']):+.1f}% 1m",
                )

    st.markdown("### 📌 Screeningstatus")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Kjøp", int((data["Signal"] == "KJØP").sum()))
    s2.metric("Hold", int((data["Signal"] == "HOLD").sum()))
    s3.metric("Selg", int((data["Signal"] == "SELG").sum()))
    s4.metric("Høy risiko", int((data["Risk Score"] >= 70).sum()))
    s5.metric("Snitt score", f"{data['Strategy Score'].mean():.1f}")

    # Desktop-style panels using native containers
    st.markdown("### 🏆 Signalpanel")
    p1, p2, p3 = st.columns(3)

    with p1:
        st.markdown("#### Top Conviction")
        top_conv = data.sort_values("Strategy Score", ascending=False).head(6)
        st.dataframe(
            formatted(top_conv[["Ticker", "Signal", "Strategy Score", "Risk Score", "Trend"]]),
            use_container_width=True,
            height=260,
        )

    with p2:
        st.markdown("#### Rakett-radar")
        rockets = data.sort_values("Rocket Score", ascending=False).head(6)
        st.dataframe(
            formatted(rockets[["Ticker", "Signal", "Rocket Score", "Risk Score", "Trend"]]),
            use_container_width=True,
            height=260,
        )

    with p3:
        st.markdown("#### Risiko")
        risky = data.sort_values("Risk Score", ascending=False).head(6)
        st.dataframe(
            formatted(risky[["Ticker", "Signal", "Risk Score", "Rocket Score", "Trend"]]),
            use_container_width=True,
            height=260,
        )

    st.markdown("### 🧭 Risk / Reward og sektorbilde")
    c1, c2 = st.columns([1.1, .9])

    with c1:
        data_dash_plot = data.copy()
        data_dash_plot["Boblestørrelse"] = positive_size_series(data_dash_plot["Rocket Score"], default=20)
        fig = px.scatter(
            data_dash_plot,
            x="Risk Score",
            y="Strategy Score",
            size="Boblestørrelse",
            color="Signal",
            hover_name="Ticker",
            hover_data=["Selskap", "Sektor", "Rocket Score", "Forklaring"],
            template=plotly_template,
            title="Risk / Reward Map",
        )
        fig.add_vline(x=70, line_dash="dash")
        fig.add_hline(y=70, line_dash="dash")
        fig.update_layout(height=430, margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig, use_container_width=True, config=chart_config)

    with c2:
        sector_dash = data.groupby("Sektor", as_index=False).agg({
            "Strategy Score": "mean",
            "Rocket Score": "mean",
            "Risk Score": "mean",
            "3 mnd %": "mean"
        }).sort_values("Strategy Score", ascending=False).head(14)
        fig = px.imshow(
            sector_dash[["Strategy Score", "Rocket Score", "Risk Score", "3 mnd %"]].T,
            x=sector_dash["Sektor"],
            y=["Strategy", "Rocket", "Risk", "3m"],
            color_continuous_scale="Viridis",
            template=plotly_template,
            title="Sektor heatmap",
        )
        fig.update_layout(height=430, margin=dict(l=10, r=10, t=45, b=10))
        st.plotly_chart(fig, use_container_width=True, config=chart_config)

    st.markdown("### 📱 Kortvisning")
    card_cols = st.columns(2)
    for i, (_, r) in enumerate(data.sort_values("Strategy Score", ascending=False).head(8).iterrows()):
        with card_cols[i % 2]:
            st.markdown(safe_render_stock_card(r, "Aksjekort"), unsafe_allow_html=True)

    
    st.markdown("### 🧠 Top Ideas Engine")

    idea1, idea2, idea3 = st.columns(3)

    with idea1:
        st.markdown("#### Beste risk/reward")
        rr_df = data.copy()
        rr_df["RR"] = rr_df["Strategy Score"] / rr_df["Risk Score"].clip(lower=1)
        st.dataframe(
            formatted(
                rr_df.sort_values("RR", ascending=False).head(5)[
                    ["Ticker", "Signal", "Strategy Score", "Risk Score", "Rocket Score"]
                ]
            ),
            use_container_width=True,
            height=220,
        )

    with idea2:
        st.markdown("#### Rakettkandidater")
        rockets = data.sort_values("Rocket Score", ascending=False).head(5)
        st.dataframe(
            formatted(
                rockets[
                    ["Ticker", "Signal", "Rocket Score", "Risk Score", "1 år %"]
                ]
            ),
            use_container_width=True,
            height=220,
        )

    with idea3:
        st.markdown("#### Defensive kandidater")
        defensive = data.sort_values(["Risk Score", "Strategy Score"], ascending=[True, False]).head(5)
        st.dataframe(
            formatted(
                defensive[
                    ["Ticker", "Signal", "Risk Score", "Strategy Score", "Value Score"]
                ]
            ),
            use_container_width=True,
            height=220,
        )

    st.markdown("### 🔍 Explain Score")

    explain_ticker = st.selectbox(
        "Velg aksje",
        data["Ticker"].tolist(),
        key="explain_score_select"
    )

    explain_row = data[data["Ticker"] == explain_ticker].iloc[0]

    e1, e2 = st.columns([1.2, .8])

    with e1:
        st.markdown(safe_render_stock_card(explain_row, "Scoreforklaring"), unsafe_allow_html=True)

    with e2:
        st.markdown("#### Scoreforklaring")
        st.code(explain_score(explain_row))

        scenario = scenario_estimates(explain_row)

        st.metric("Bull case", f"+{scenario['bull']:.0f}%")
        st.metric("Base case", f"+{scenario['base']:.0f}%")
        st.metric("Bear case", f"{scenario['bear']:.0f}%")
        st.metric("Risk/Reward", f"{scenario['rr']:.1f}x")


    st.markdown("### 📊 Full signaltabell")
    st.dataframe(formatted(data[show_cols]), use_container_width=True, height=460)

    st.markdown("### Dagens movers")
    movers_col1, movers_col2 = st.columns(2)
    with movers_col1:
        winners = data.sort_values("Dagsendring %", ascending=False).head(8)
        fig = px.bar(winners, x="Ticker", y="Dagsendring %", color="Dagsendring %", template=plotly_template, title="Vinnere")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True, config=chart_config)
    with movers_col2:
        losers = data.sort_values("Dagsendring %", ascending=True).head(8)
        fig = px.bar(losers, x="Ticker", y="Dagsendring %", color="Dagsendring %", template=plotly_template, title="Tapere")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True, config=chart_config)

with tabs[1]:
    st.subheader("Top Conviction Picks")
    conviction = data.copy()
    conviction["Conviction Score"] = (
        0.55 * conviction["Strategy Score"] +
        0.20 * conviction["Investment Score"] +
        0.15 * conviction["Rocket Score"] +
        0.10 * (100 - conviction["Risk Score"])
    ).clip(0, 100)
    conviction = conviction.sort_values("Conviction Score", ascending=False).head(10)

    st.markdown('<div class="terminal-card"><h3>Hva betyr Conviction?</h3><div class="subtle">En samlet vurdering av strategi-score, kvalitet, momentum, rakettpotensial og risiko. Dette er et analysesignal, ikke en kjøpsanbefaling.</div></div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, (_, r) in enumerate(conviction.iterrows()):
        with cols[i % 2]:
            st.markdown(safe_render_stock_card(r, "Aksjekort"), unsafe_allow_html=True)


with tabs[2]:
    st.subheader("Historiske scores i SQLite")
    selected_hist = st.selectbox("Velg aksje", data["Ticker"].tolist(), key="hist_ticker")
    fig = plot_score_history(selected_hist, strategy, plotly_template)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config=chart_config)
    else:
        st.info("Ingen historikk enda. Kjør appen flere dager for å bygge scorehistorikk.")
    hist = load_score_history(strategy)
    if not hist.empty:
        recent = hist.sort_values(["ticker", "run_date"]).groupby("ticker").tail(2)
        changes = []
        for ticker, group in recent.groupby("ticker"):
            if len(group) >= 2:
                g = group.sort_values("run_date")
                delta = g.iloc[-1]["strategy_score"] - g.iloc[0]["strategy_score"]
                changes.append({"Ticker": ticker, "Endring Strategy Score": delta})
        if changes:
            ch = pd.DataFrame(changes).sort_values("Endring Strategy Score", ascending=False)
            st.dataframe(ch.style.format({"Endring Strategy Score": "{:+.1f}"}), use_container_width=True)

with tabs[3]:
    st.subheader("Market regime")
    c1, c2, c3 = st.columns(3)
    c1.metric("Regime", regime)
    c2.metric("Risk-on score", f"{risk_on_score:.1f}/100")
    c3.metric("Kommentar", regime_comment)
    st.dataframe(macro_df.style.format({"Siste": "{:.2f}", "6m %": "{:+.1f}%", "1m %": "{:+.1f}%"}), use_container_width=True)
    fig = px.bar(macro_df, x="Asset", y="1m %", color="1m %", template=plotly_template, title="Makroassets siste måned")
    st.plotly_chart(fig, use_container_width=True, config=chart_config)

with tabs[4]:
    st.subheader("Sektorrotasjon")
    st.dataframe(sector_perf.style.format({"3 mnd %": "{:+.1f}%", "Strategy Score": "{:.1f}", "Risk Score": "{:.1f}"}), use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(sector_perf, x="Sektor", y="3 mnd %", color="3 mnd %", template=plotly_template, title="Sektor momentum 3 mnd")
        st.plotly_chart(fig, use_container_width=True, config=chart_config)
    with col2:
        sector_perf_plot = sector_perf.copy()
        sector_perf_plot["Boblestørrelse"] = positive_size_series(sector_perf_plot["3 mnd %"], default=8)
        fig = px.scatter(sector_perf_plot, x="Risk Score", y="Strategy Score", size="Boblestørrelse", hover_name="Sektor", template=plotly_template, title="Sektor risk/reward")
        st.plotly_chart(fig, use_container_width=True, config=chart_config)

with tabs[5]:
    st.subheader("Teknisk analyse")
    selected = st.selectbox("Velg aksje", data["Ticker"].tolist(), key="tech_ticker")
    st.plotly_chart(plot_candlestick(selected, plotly_template), use_container_width=True, config=chart_config)
    selected_row = data[data["Ticker"] == selected].iloc[0]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Signal", selected_row["Signal"])
    c2.metric("Teknisk Score", f"{selected_row['Teknisk Score']:.1f}")
    c3.metric("RSI", f"{selected_row['RSI']:.1f}")
    c4.metric("Trend", selected_row["Trend"])
    c5.metric("Risk Score", f"{selected_row['Risk Score']:.1f}")

with tabs[6]:
    st.subheader("Risikomatrise")
    data_risk_plot = data.copy()
    data_risk_plot["Boblestørrelse"] = positive_size_series(data_risk_plot["Rocket Score"], default=20)
    fig = px.scatter(data_risk_plot, x="Risk Score", y="Strategy Score", size="Boblestørrelse", color="Signal", hover_name="Ticker", template=plotly_template)
    fig.add_vline(x=70, line_dash="dash")
    fig.add_hline(y=70, line_dash="dash")
    fig.update_layout(height=540)
    st.plotly_chart(fig, use_container_width=True, config=chart_config)

with tabs[7]:
    st.subheader("Porteføljerisiko 2.0")
    pf = load_portfolio()

    with st.expander("Legg til posisjon"):
        pc1, pc2, pc3 = st.columns(3)
        p_ticker = pc1.text_input("Ticker")
        p_shares = pc2.number_input("Antall aksjer", min_value=0.0, value=0.0)
        p_cost = pc3.number_input("Kjøpskurs", min_value=0.0, value=0.0)
        if st.button("Legg til i portefølje"):
            if p_ticker.strip() and p_shares > 0:
                pf = pd.concat([pf, pd.DataFrame([{"ticker": p_ticker.upper().strip(), "shares": p_shares, "cost_price": p_cost}])], ignore_index=True)
                save_portfolio(pf)
                st.success("Posisjon lagt til.")
            else:
                st.warning("Legg inn ticker og antall.")

    if pf.empty:
        st.info("Ingen portefølje enda.")
    else:
        price_map = dict(zip(data["Ticker"], data["Siste kurs"]))
        sector_map = dict(zip(data["Ticker"], data["Sektor"]))
        signal_map = dict(zip(data["Ticker"], data["Signal"]))
        risk_map = dict(zip(data["Ticker"], data["Risk Score"]))
        score_map = dict(zip(data["Ticker"], data["Strategy Score"]))

        pf["last_price"] = pf["ticker"].map(price_map).fillna(pf["cost_price"])
        pf["sector"] = pf["ticker"].map(sector_map).fillna("Ukjent")
        pf["market_value"] = pf["shares"] * pf["last_price"]
        pf["cost_value"] = pf["shares"] * pf["cost_price"]
        pf["return_%"] = np.where(pf["cost_value"] > 0, (pf["market_value"] / pf["cost_value"] - 1) * 100, 0)
        pf["Signal"] = pf["ticker"].map(signal_map).fillna("N/A")
        pf["Risk Score"] = pf["ticker"].map(risk_map).fillna(50)
        pf["Strategy Score"] = pf["ticker"].map(score_map).fillna(50)
        total_value = pf["market_value"].sum()
        pf["weight_%"] = np.where(total_value > 0, pf["market_value"] / total_value * 100, 0)
        weighted_risk = (pf["Risk Score"] * pf["weight_%"] / 100).sum()
        weighted_score = (pf["Strategy Score"] * pf["weight_%"] / 100).sum()
        max_pos = pf["weight_%"].max()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Porteføljeverdi", f"{total_value:,.0f}")
        c2.metric("Vektet risiko", f"{weighted_risk:.1f}")
        c3.metric("Vektet score", f"{weighted_score:.1f}")
        c4.metric("Største posisjon", f"{max_pos:.1f}%")

        warnings = []
        if weighted_risk > 70:
            warnings.append("⚠️ Porteføljen har høy vektet risikoscore.")
        if max_pos > 30:
            warnings.append("⚠️ Én posisjon utgjør mer enn 30 % av porteføljen.")
        sector_weights = pf.groupby("sector")["market_value"].sum() / total_value * 100 if total_value > 0 else pd.Series(dtype=float)
        if not sector_weights.empty and sector_weights.max() > 45:
            warnings.append(f"⚠️ Høy sektorkonsentrasjon: {sector_weights.idxmax()} utgjør {sector_weights.max():.1f} %.")
        if warnings:
            for w in warnings:
                st.markdown(f'<div class="danger-card">{w}</div>', unsafe_allow_html=True)
        else:
            st.success("Ingen store porteføljerisiko-varsler basert på dagens enkle regler.")

        st.dataframe(pf.style.format({
            "shares": "{:.2f}", "cost_price": "{:.2f}", "last_price": "{:.2f}",
            "market_value": "{:,.0f}", "cost_value": "{:,.0f}", "return_%": "{:+.1f}%",
            "Risk Score": "{:.1f}", "Strategy Score": "{:.1f}", "weight_%": "{:.1f}%"
        }), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(pf, names="ticker", values="market_value", template=plotly_template, title="Posisjonsvekter")
            st.plotly_chart(fig, use_container_width=True, config=chart_config)
        with col2:
            sector_df = pf.groupby("sector", as_index=False)["market_value"].sum()
            fig = px.pie(sector_df, names="sector", values="market_value", template=plotly_template, title="Sektorfordeling")
            st.plotly_chart(fig, use_container_width=True, config=chart_config)

with tabs[8]:
    st.subheader("Notater og investeringshypoteser")
    notes = load_notes()
    with st.expander("Legg til notat"):
        nc1, nc2 = st.columns(2)
        n_ticker = nc1.selectbox("Ticker", data["Ticker"].tolist())
        n_status = nc2.selectbox("Status", ["Åpen", "Overvåk", "Avvist", "Kjøpt"])
        n_note = st.text_area("Notat")
        if st.button("Lagre notat"):
            new = pd.DataFrame([{"ticker": n_ticker, "date": str(date.today()), "note": n_note, "status": n_status}])
            notes = pd.concat([notes, new], ignore_index=True)
            save_notes(notes)
            st.success("Notat lagret.")
    st.dataframe(notes, use_container_width=True)

with tabs[9]:
    st.subheader("ChatGPT-promptgenerator")
    selected_prompt = st.selectbox("Velg aksje", data["Ticker"].tolist(), key="prompt_ticker")
    row = data[data["Ticker"] == selected_prompt].iloc[0]
    st.text_area("Kopier til ChatGPT", value=make_prompt(row, regime, daily_brief), height=460)

with tabs[10]:
    st.subheader("Eksport")
    st.download_button("Last ned screening CSV", data=data.to_csv(index=False).encode("utf-8"), file_name="investai_v7_1_screening.csv", mime="text/csv")
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Screening")
        macro_df.to_excel(writer, index=False, sheet_name="Market Regime")
        sector_perf.to_excel(writer, index=False, sheet_name="Sector Rotation")
        load_score_history(strategy).to_excel(writer, index=False, sheet_name="Score History")
        load_portfolio().to_excel(writer, index=False, sheet_name="Portfolio")
    st.download_button("Last ned Excel", data=excel_buffer.getvalue(), file_name="investai_v7_1_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("---")
st.caption("Disclaimer: InvestAI v7.1 gir modellbaserte analyser og signaler. Dette er ikke personlig finansiell rådgivning.")
