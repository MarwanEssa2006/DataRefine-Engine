"""
╔══════════════════════════════════════════════════════════════╗
║           DATA INTELLIGENCE ENGINE  —  Streamlit UI         ║
║                                                              ║
║  Tab 1 → Executive Summary  (KPIs + Charts)                  ║
║  Tab 2 → Bill of Health     (Full Audit Table)               ║
║  Tab 3 → Smart Clean        (Permission Panel + Run)         ║
║  Tab 4 → SQL Schema         (Auto-generated CREATE TABLE)    ║
╚══════════════════════════════════════════════════════════════╝

Run:
    pip install streamlit plotly rapidfuzz scipy
    streamlit run app.py
"""

import io
import sys
import tempfile
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─── page config (must be first Streamlit call) ───────────────
st.set_page_config(
    page_title="Data Intelligence Engine",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=JetBrains+Mono:wght@300;400;600&display=swap');

/* ══ DESIGN TOKENS ══════════════════════════════════════════ */
:root {
    --bg:        #060809;
    --surface:   #0c1014;
    --surface2:  #111820;
    --border:    #1c2a35;
    --border2:   #243040;
    --accent:    #00e5a0;
    --accent2:   #00b87a;
    --danger:    #ff4444;
    --warn:      #ffb347;
    --text:      #dce8f0;
    --muted:     #4a6070;
    --mono:      'JetBrains Mono', monospace;
    --display:   'Syne', sans-serif;
}

/* ══ GLOBAL ═════════════════════════════════════════════════ */
html, body, [class*="css"], .stApp {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
}

/* scanline texture overlay */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,229,160,0.015) 2px,
        rgba(0,229,160,0.015) 4px
    );
    pointer-events: none;
    z-index: 9999;
}

/* ══ SIDEBAR ════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] > div { padding-top: 1.5rem; }
section[data-testid="stSidebar"] * { color: var(--text) !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: var(--accent) !important;
    color: #000 !important;
    font-family: var(--mono) !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 2px !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.15s ease !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--accent2) !important;
    box-shadow: 0 0 20px rgba(0,229,160,0.35) !important;
    transform: translateY(-1px) !important;
}

/* ══ MAIN AREA ══════════════════════════════════════════════ */
.main .block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 4rem !important;
    max-width: 1400px !important;
}

/* ══ HEADINGS ═══════════════════════════════════════════════ */
h1, h2 {
    font-family: var(--display) !important;
    font-weight: 800 !important;
    color: var(--text) !important;
    letter-spacing: -0.02em !important;
    border: none !important;
}
h3 {
    font-family: var(--mono) !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: var(--accent) !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 0.5rem !important;
}

/* ══ KPI METRIC CARDS ═══════════════════════════════════════ */
div[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-top: 2px solid var(--accent) !important;
    border-radius: 0 !important;
    padding: 1.1rem 1.3rem !important;
    position: relative !important;
    overflow: hidden !important;
}
div[data-testid="metric-container"]::after {
    content: '';
    position: absolute;
    bottom: 0; right: 0;
    width: 40px; height: 40px;
    background: linear-gradient(135deg, transparent 50%, rgba(0,229,160,0.06) 50%);
}
div[data-testid="metric-container"] label {
    font-family: var(--mono) !important;
    font-size: 0.65rem !important;
    letter-spacing: 0.15em !important;
    color: var(--muted) !important;
    text-transform: uppercase !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: var(--mono) !important;
    font-size: 2rem !important;
    font-weight: 600 !important;
    color: var(--accent) !important;
    line-height: 1.1 !important;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
}

/* ══ TABS ═══════════════════════════════════════════════════ */
div[data-testid="stTabs"] > div:first-child {
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
}
button[data-baseweb="tab"] {
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    font-weight: 400 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: var(--muted) !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.7rem 1.2rem !important;
    transition: all 0.15s !important;
}
button[data-baseweb="tab"]:hover { color: var(--text) !important; }
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: transparent !important;
}

/* ══ EXPANDERS ══════════════════════════════════════════════ */
details {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 0 !important;
    margin-bottom: 6px !important;
}
details summary {
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
    padding: 0.7rem 1rem !important;
    cursor: pointer !important;
    color: var(--text) !important;
}
details[open] { border-left: 2px solid var(--accent) !important; }

/* ══ BUTTONS ════════════════════════════════════════════════ */
.stButton > button {
    background: transparent !important;
    color: var(--accent) !important;
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border: 1px solid var(--accent) !important;
    border-radius: 2px !important;
    padding: 0.55rem 1.2rem !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: var(--accent) !important;
    color: #000 !important;
    box-shadow: 0 0 24px rgba(0,229,160,0.3) !important;
}
.stButton > button:disabled {
    opacity: 0.3 !important;
    cursor: not-allowed !important;
}

/* ══ DOWNLOAD BUTTONS ═══════════════════════════════════════ */
.stDownloadButton > button {
    background: var(--surface2) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.08em !important;
    border: 1px solid var(--border2) !important;
    border-radius: 2px !important;
}
.stDownloadButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* ══ INPUTS / SELECTS ═══════════════════════════════════════ */
.stTextInput input, .stSelectbox select,
div[data-baseweb="select"] > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
}
.stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(0,229,160,0.15) !important;
}
.stSlider [data-testid="stThumbValue"] {
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    color: var(--accent) !important;
}
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}

/* ══ CHECKBOXES ═════════════════════════════════════════════ */
.stCheckbox label {
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    color: var(--text) !important;
}
.stCheckbox input[type="checkbox"]:checked + div {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}

/* ══ DATAFRAMES ═════════════════════════════════════════════ */
.stDataFrame {
    border: 1px solid var(--border) !important;
    border-radius: 0 !important;
}
.stDataFrame th {
    background: var(--surface2) !important;
    color: var(--muted) !important;
    font-family: var(--mono) !important;
    font-size: 0.68rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--border) !important;
}
.stDataFrame td {
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
}

/* ══ CODE BLOCKS ════════════════════════════════════════════ */
pre, code {
    font-family: var(--mono) !important;
    font-size: 0.78rem !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    color: var(--accent) !important;
}

/* ══ ALERTS / INFO ══════════════════════════════════════════ */
.stAlert {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 0 !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
}

/* ══ MULTISELECT ════════════════════════════════════════════ */
span[data-baseweb="tag"] {
    background: rgba(0,229,160,0.12) !important;
    border: 1px solid var(--accent) !important;
    border-radius: 2px !important;
    color: var(--accent) !important;
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
}

/* ══ DIVIDER ════════════════════════════════════════════════ */
hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }

/* ══ SPINNER ════════════════════════════════════════════════ */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* ══ SUCCESS / ERROR ════════════════════════════════════════ */
.stSuccess { border-left: 3px solid var(--accent) !important; }
.stError   { border-left: 3px solid var(--danger) !important; }

/* ══ SCROLLBAR ══════════════════════════════════════════════ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _badge(severity: str) -> str:
    styles = {
        "HIGH":   "background:#3d0f0f;color:#ff4444;border:1px solid #ff444466;",
        "MEDIUM": "background:#2d1e05;color:#ffb347;border:1px solid #ffb34766;",
        "OK":     "background:#0a1f12;color:#00e5a0;border:1px solid #00e5a066;",
    }
    style = styles.get(severity, styles["OK"])
    return (
        f'<span style="{style}padding:2px 10px;border-radius:2px;'
        f'font-size:.72rem;font-family:\'JetBrains Mono\',monospace;'
        f'letter-spacing:.08em;text-transform:uppercase;">{severity}</span>'
    )


def _sql_type_for(col_series: pd.Series, dialect: str = "postgresql") -> str:
    """
    Smart SQL type mapper — reads actual data, not just dtype label.

    Rules (applied in priority order):
      1. bool        → BIT (sql server) | BOOLEAN (pg/mysql)
      2. datetime    → DATETIME (sql server) | TIMESTAMP (pg/mysql)
      3. integer     → TINYINT / SMALLINT / INT / BIGINT  (sized by max value)
      4. float       → DECIMAL(18,2)  (safe for money/metrics)
      5. object/cat  → VARCHAR(N)  where N = max_len * 1.25, rounded to nearest 50,
                        min 50, max 4000; TEXT if > 4000
    """
    dtype = str(col_series.dtype)
    s     = col_series.dropna()

    # ── bool ──────────────────────────────────────────────────
    if "bool" in dtype:
        return "BIT" if dialect == "sqlserver" else "BOOLEAN"

    # ── datetime ──────────────────────────────────────────────
    if "datetime" in dtype:
        return "DATETIME" if dialect == "sqlserver" else "TIMESTAMP"

    # ── integer — size by actual range ────────────────────────
    if pd.api.types.is_integer_dtype(col_series):
        try:
            mx = int(s.abs().max()) if len(s) else 0
            if mx <= 127:       return "TINYINT"
            if mx <= 32_767:    return "SMALLINT"
            if mx <= 2_147_483_647: return "INT"
            return "BIGINT"
        except Exception:
            return "BIGINT"

    # ── float ─────────────────────────────────────────────────
    if pd.api.types.is_float_dtype(col_series):
        return "DECIMAL(18,2)"

    # ── string / category — sized VARCHAR ─────────────────────
    try:
        max_len = int(col_series.astype(str).str.len().max()) if len(s) else 50
    except Exception:
        max_len = 255
    # round up to nearest 50, add 25% buffer, min 50
    padded  = max(50, int(max_len * 1.25))
    rounded = int(np.ceil(padded / 50) * 50)
    if rounded > 4000:
        return "TEXT" if dialect in ("postgresql","mysql") else "NVARCHAR(MAX)"
    return f"VARCHAR({rounded})"


def _detect_primary_key(df: pd.DataFrame) -> str | None:
    """
    Heuristic PK detection:
    - column name contains 'id' (case-insensitive)
    - all values unique
    - no nulls
    Returns column name or None.
    """
    pk_keywords = ["id", "key", "code", "uuid", "pk"]
    for col in df.columns:
        col_l = col.lower().replace(" ", "_")
        is_id_name = any(k in col_l for k in pk_keywords)
        if is_id_name and df[col].nunique() == len(df) and df[col].isnull().sum() == 0:
            return col
    return None


def generate_sql_schema(
    df: pd.DataFrame,
    table_name: str = "cleaned_data",
    dialect: str    = "postgresql",
    schema: str     = "",
    pk_col: str     = None,
) -> str:
    """
    Smart CREATE TABLE generator.
    - Sized VARCHARs (not lazy TEXT everywhere)
    - Integer range detection (TINYINT → BIGINT)
    - DECIMAL(18,2) for floats
    - Auto PRIMARY KEY detection
    - NOT NULL flags
    - Dialect: postgresql | mysql | sqlserver
    """
    pk_col    = pk_col or _detect_primary_key(df)
    qual_name = f"{schema}.{table_name}" if schema else table_name

    # dialect-specific bracket style
    q = "[{}]" if dialect == "sqlserver" else "{}"

    lines = []
    for col in df.columns:
        sql_type  = _sql_type_for(df[col], dialect)
        null_flag = "" if df[col].isnull().any() else " NOT NULL"
        pk_flag   = " PRIMARY KEY" if col == pk_col else ""
        col_name  = q.format(col)
        lines.append(f"    {col_name:<40} {sql_type}{null_flag}{pk_flag}")

    body = ",\n".join(lines)
    header = (
        f"-- Generated by Data Intelligence Engine\n"
        f"-- Dialect : {dialect.upper()}\n"
        f"-- Source  : {len(df):,} rows × {len(df.columns)} cols\n"
        f"-- {'-'*55}\n"
    )
    return f"{header}CREATE TABLE {qual_name} (\n{body}\n);"


def build_actionable_insights(report: dict, df: pd.DataFrame) -> list[dict]:
    """
    Reads the Auditor's report and returns a list of plain-language
    business-level recommendations — one per real issue found.

    Each item:
        {
          "severity": "HIGH" | "MEDIUM" | "LOW",
          "icon":     emoji,
          "title":    short headline,
          "body":     actionable sentence for the manager,
          "impact":   who / what is affected,
        }
    """
    insights = []
    checks   = report.get("checks", {})
    rows     = report["shape"]["rows"]

    # ── Nulls ─────────────────────────────────────────────────
    null_check = checks.get("nulls", {})
    if null_check.get("found"):
        by_col = null_check.get("by_column", {})
        for col, info in by_col.items():
            pct = info.get("pct", 0)
            if pct >= 30:
                sev    = "HIGH"
                impact = _null_impact_sentence(col, pct)
                insights.append({
                    "severity": sev,
                    "icon": "⚠️",
                    "title": f"Critical gap in '{col}'",
                    "body":  (
                        f"Column '{col}' is {pct:.1f}% empty. "
                        f"Any analysis or model trained on this column will be unreliable."
                    ),
                    "impact": impact,
                })
            elif pct >= 10:
                insights.append({
                    "severity": "MEDIUM",
                    "icon": "📉",
                    "title": f"Partial data in '{col}'",
                    "body":  f"'{col}' has {pct:.1f}% missing values ({info['count']:,} rows). Imputation recommended before reporting.",
                    "impact": "May skew averages and segment totals.",
                })

    # ── Duplicates ────────────────────────────────────────────
    dup_check = checks.get("duplicates", {})
    if dup_check.get("found"):
        count = dup_check["count"]
        pct   = dup_check.get("pct", round(count / max(rows, 1) * 100, 1))
        insights.append({
            "severity": "HIGH" if pct > 5 else "MEDIUM",
            "icon": "🔁",
            "title": f"{count:,} duplicate rows detected",
            "body":  (
                f"{pct:.1f}% of records are exact duplicates. "
                f"This inflates totals, averages, and any KPI built on row count."
            ),
            "impact": "Financial reports and dashboards will show incorrect figures.",
        })

    # ── Outliers ──────────────────────────────────────────────
    out_check = checks.get("outliers", {})
    if out_check.get("found"):
        by_col = out_check.get("by_column", {})
        for col, info in list(by_col.items())[:3]:   # top 3 worst
            n = info.get("zscore_outliers", 0)
            insights.append({
                "severity": "MEDIUM",
                "icon": "📊",
                "title": f"Extreme values in '{col}'",
                "body":  (
                    f"{n} rows in '{col}' are statistical outliers (Z-score > 3). "
                    f"Valid range: {info.get('iqr_lower')} – {info.get('iqr_upper')}."
                ),
                "impact": "Could indicate data entry errors or genuine anomalies worth investigating.",
            })

    # ── PII ───────────────────────────────────────────────────
    pii_check = checks.get("pii", {})
    if pii_check.get("found"):
        cols = pii_check.get("columns", [])
        insights.append({
            "severity": "HIGH",
            "icon": "🔒",
            "title": f"Personal data detected ({len(cols)} column{'s' if len(cols)>1 else ''})",
            "body":  (
                f"Columns {cols} may contain PII. "
                f"Sharing or storing this data unmasked may violate GDPR / local privacy regulations."
            ),
            "impact": "Legal and compliance risk. Mask or hash before sharing externally.",
        })

    # ── Sparse columns ────────────────────────────────────────
    sparse_check = checks.get("sparse_columns", {})
    if sparse_check.get("found"):
        n = sparse_check["count"]
        insights.append({
            "severity": "MEDIUM",
            "icon": "🕳️",
            "title": f"{n} mostly-empty column{'s' if n>1 else ''}",
            "body":  f"{n} column(s) are more than 50% empty and add noise without value.",
            "impact": "Drop them to reduce storage and avoid misleading analysis.",
        })

    # ── Typos ─────────────────────────────────────────────────
    typo_check = checks.get("typos", {})
    if typo_check.get("found"):
        n_cols = len(typo_check.get("by_column", {}))
        insights.append({
            "severity": "MEDIUM",
            "icon": "🔤",
            "title": f"Spelling inconsistencies in {n_cols} column{'s' if n_cols>1 else ''}",
            "body":  "Near-duplicate values found (e.g. 'Cairo' vs 'Caïro'). Grouping and filtering will produce wrong results.",
            "impact": "Segment-level reports and pivot tables will be fragmented.",
        })

    # ── Correlation ───────────────────────────────────────────
    corr_check = checks.get("high_correlation", {})
    if corr_check.get("found"):
        pairs = corr_check.get("pairs", [])
        if pairs:
            p = pairs[0]
            insights.append({
                "severity": "LOW",
                "icon": "🔗",
                "title": f"Redundant columns: '{p['col_a']}' ↔ '{p['col_b']}'",
                "body":  (
                    f"These two columns are {p['correlation']*100:.0f}% correlated. "
                    f"Keeping both in a model will cause multicollinearity."
                ),
                "impact": "Drop one before building regression or ML models.",
            })

    # ── No issues ─────────────────────────────────────────────
    if not insights:
        insights.append({
            "severity": "LOW",
            "icon": "✅",
            "title": "No critical issues found",
            "body":  "Your dataset passed all major quality checks.",
            "impact": "Ready for analysis.",
        })

    # Sort: HIGH first
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    insights.sort(key=lambda x: order.get(x["severity"], 3))
    return insights


def _null_impact_sentence(col: str, pct: float) -> str:
    """Heuristic: guess business impact from column name."""
    col_l = col.lower()
    if any(k in col_l for k in ["phone", "mobile", "tel"]):
        return f"Direct impact on contact campaigns — {pct:.0f}% of customers unreachable."
    if any(k in col_l for k in ["email", "mail"]):
        return f"Email marketing reach reduced by ~{pct:.0f}%."
    if any(k in col_l for k in ["price", "revenue", "amount", "sales", "cost"]):
        return f"Financial totals will be understated by up to {pct:.0f}%."
    if any(k in col_l for k in ["date", "time", "created", "updated"]):
        return f"Time-series analysis and trend reports will have gaps."
    if any(k in col_l for k in ["name", "customer", "client", "user"]):
        return f"Record identification and deduplication will be incomplete."
    if any(k in col_l for k in ["age", "gender", "region", "city", "country"]):
        return f"Demographic segmentation will be skewed."
    return f"Downstream models and reports depending on '{col}' will be affected."


def _sev_color(sev: str) -> str:
    return {"HIGH": "#ff4444", "MEDIUM": "#ffb347", "LOW": "#00e5a0"}.get(sev, "#4a6070")


def _sev_bg(sev: str) -> str:
    return {"HIGH": "#1a0808", "MEDIUM": "#1a1008", "LOW": "#061a10"}.get(sev, "#0c1014")


def _score_color(score: int) -> str:
    if score >= 90: return "#00e5a0"
    if score >= 75: return "#ffb347"
    if score >= 55: return "#ff8c42"
    return "#ff4444"


def make_gauge(score: int, title: str = "Data Health Score") -> go.Figure:
    color = _score_color(score)
    fig = go.Figure(go.Indicator(
        mode  = "gauge+number",
        value = score,
        number= {"suffix": "%", "font": {"color": "#dce8f0", "size": 48, "family": "JetBrains Mono"}},
        title = {"text": title, "font": {"color": "#4a6070", "size": 12, "family": "JetBrains Mono"}},
        gauge = {
            "axis":  {"range": [0, 100], "tickcolor": "#1c2a35",
                      "tickfont": {"color": "#4a6070", "family": "JetBrains Mono", "size": 10}},
            "bar":   {"color": color, "thickness": 0.6},
            "bgcolor": "#0c1014",
            "bordercolor": "#1c2a35",
            "steps": [
                {"range": [0,  55], "color": "#0f1a22"},
                {"range": [55, 75], "color": "#0f1a22"},
                {"range": [75, 90], "color": "#0f1a22"},
                {"range": [90,100], "color": "#0f1a22"},
            ],
            "threshold": {
                "line": {"color": color, "width": 2},
                "thickness": 0.8,
                "value": score,
            },
        }
    ))
    fig.update_layout(
        height        = 270,
        margin        = dict(t=50, b=10, l=20, r=20),
        paper_bgcolor = "#060809",
        font_color    = "#dce8f0",
    )
    return fig


# px.*() only accepts 'template' from these keys
_DARK = dict(template="plotly_dark")

# full layout dict for update_layout() calls
_DARK_LAYOUT = dict(
    template     = "plotly_dark",
    paper_bgcolor= "#060809",
    plot_bgcolor = "#0c1014",
    font         = dict(family="JetBrains Mono, monospace", color="#dce8f0", size=11),
)


# ══════════════════════════════════════════════════════════════
# SIDEBAR — file upload + settings
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:1.3rem;font-weight:800;"
        "color:#00e5a0;letter-spacing:-0.01em;margin-bottom:2px;'>DATA INTELLIGENCE</div>"
        "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.65rem;"
        "color:#4a6070;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:1.2rem;'>"
        "ENGINE v4.0</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='width:100%;height:1px;background:linear-gradient("
        "90deg,#00e5a0,transparent);margin-bottom:1.2rem;'></div>",
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Drop your data file here",
        type=["csv", "xlsx", "xls", "json", "parquet"],
        help="Supports CSV, Excel, JSON, Parquet"
    )

    if uploaded_file:
        st.markdown("#### ⚙️ Audit Settings")
        corr_threshold = st.slider(
            "Correlation threshold",
            min_value=0.5, max_value=1.0, value=0.95, step=0.01,
            help="Higher = less aggressive correlation dropping"
        )
        skew_threshold = st.slider(
            "Skew threshold (impute)",
            min_value=0.3, max_value=3.0, value=1.0, step=0.1,
            help="If |skew| > this → use median instead of mean"
        )
        st.markdown("---")
        run_btn = st.button("🚀 Run Deep Audit", use_container_width=True)
        st.markdown("---")
        st.markdown(
            "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;"
            "color:#1c2a35;letter-spacing:0.1em;'>BUILT ON DATAAUDITOR v4</div>",
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════
# MAIN — guard: nothing uploaded yet
# ══════════════════════════════════════════════════════════════

if not uploaded_file:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:3rem;font-weight:800;"
        "color:#dce8f0;letter-spacing:-0.03em;line-height:1;margin-bottom:0.3rem;'>"
        "DATA<br>"
        "<span style='color:#00e5a0;'>INTELLIGENCE</span>"
        "</div>"
        "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.72rem;"
        "color:#4a6070;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:2rem;'>"
        "AUDIT ENGINE · UPLOAD A FILE TO BEGIN</div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<div style='width:120px;height:2px;background:linear-gradient(90deg,#00e5a0,transparent);"
        "margin-bottom:2.5rem;'></div>",
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    for col, num, label, desc in [
        (c1, "01", "Audit",    "17 quality checks · zero modifications"),
        (c2, "02", "Approve",  "You decide what gets fixed"),
        (c3, "03", "Clean",    "Only approved ops execute"),
        (c4, "04", "Export",   "CSV · Excel · SQL Schema ready"),
    ]:
        col.markdown(f"""
        <div style='
            background:#0c1014;
            border:1px solid #1c2a35;
            border-top:2px solid #00e5a0;
            padding:1.4rem 1.2rem;
            position:relative;
        '>
            <div style='
                font-family:"Syne",sans-serif;
                font-size:2.2rem;
                font-weight:800;
                color:#1c2a35;
                line-height:1;
                margin-bottom:0.6rem;
            '>{num}</div>
            <div style='
                font-family:"JetBrains Mono",monospace;
                font-size:0.75rem;
                font-weight:600;
                color:#00e5a0;
                letter-spacing:0.12em;
                text-transform:uppercase;
                margin-bottom:0.4rem;
            '>{label}</div>
            <div style='
                font-family:"JetBrains Mono",monospace;
                font-size:0.7rem;
                color:#4a6070;
                line-height:1.5;
            '>{desc}</div>
        </div>
        """, unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════
# LOAD FILE into a temp path so DataAuditor can read it
# ══════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def load_raw(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    ext = file_name.rsplit(".", 1)[-1].lower()
    buf = io.BytesIO(file_bytes)
    loaders = {
        "csv":     lambda: pd.read_csv(buf),
        "xlsx":    lambda: pd.read_excel(buf),
        "xls":     lambda: pd.read_excel(buf),
        "json":    lambda: pd.read_json(buf),
        "parquet": lambda: pd.read_parquet(buf),
    }
    return loaders[ext]()


raw_bytes = uploaded_file.read()
df_raw    = load_raw(raw_bytes, uploaded_file.name)

# Save to a temp file so DataAuditor (which needs a path) can load it
_tmp = tempfile.NamedTemporaryFile(
    suffix="." + uploaded_file.name.rsplit(".", 1)[-1].lower(),
    delete=False
)
_tmp.write(raw_bytes)
_tmp.flush()
_tmp_path = _tmp.name
_tmp.close()


# ══════════════════════════════════════════════════════════════
# RUN AUDIT (cached in session_state)
# ══════════════════════════════════════════════════════════════

if "audit_report" not in st.session_state:
    st.session_state.audit_report  = None
    st.session_state.clean_df      = None
    st.session_state.audit_log     = []
    st.session_state.clean_summary = None
    st.session_state.file_name     = None

# Reset if a new file was uploaded
if st.session_state.file_name != uploaded_file.name:
    st.session_state.audit_report  = None
    st.session_state.clean_df      = None
    st.session_state.audit_log     = []
    st.session_state.clean_summary = None
    st.session_state.file_name     = uploaded_file.name

if run_btn or st.session_state.audit_report is None:
    with st.spinner("🔍  Running 17 quality checks…"):
        try:
            # Import here so Streamlit doesn't fail on import if file not present
            sys.path.insert(0, os.path.dirname(__file__))
            from data_auditor_v4 import DataAuditor  # type: ignore

            auditor = DataAuditor(_tmp_path)
            report  = auditor.run_audit(corr_threshold=corr_threshold)
            st.session_state.audit_report = report
            st.session_state.auditor      = auditor
        except ImportError:
            st.error(
                "⚠️ `data_auditor_v4.py` not found next to `app.py`. "
                "Place both files in the same directory."
            )
            st.stop()
        except Exception as e:
            st.error(f"Audit failed: {e}")
            st.stop()

report = st.session_state.audit_report
checks = report["checks"]


# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊  Executive Summary",
    "📋  Bill of Health",
    "🧹  Smart Clean",
    "🔒  Privacy & Security",
    "🛠️  SQL Schema",
    "📈  Dashboard",
])


# ─────────────────────────────────────────────
# TAB 1 — EXECUTIVE SUMMARY
# ─────────────────────────────────────────────
with tab1:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:1.8rem;font-weight:800;"
        "color:#dce8f0;letter-spacing:-0.02em;margin-bottom:0.2rem;'>Executive Summary</div>"
        "<div style='width:60px;height:2px;background:#00e5a0;margin-bottom:1.5rem;'></div>",
        unsafe_allow_html=True
    )

    # ── KPI row ──────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Rows",          f"{report['shape']['rows']:,}")
    k2.metric("Columns",       report['shape']['cols'])
    k3.metric("Issues Found",  f"{report['issues_found']} / {len(checks)}")

    null_check = checks.get("nulls", {})
    k4.metric("Missing Values", f"{null_check.get('total', 0):,}")

    dup_check = checks.get("duplicates", {})
    k5.metric("Duplicates",    f"{dup_check.get('count', 0):,}")

    st.markdown("---")

    # ── Smart Actionable Insights ─────────────────────────────
    insights = build_actionable_insights(report, df_raw)
    high_count   = sum(1 for i in insights if i["severity"] == "HIGH")
    medium_count = sum(1 for i in insights if i["severity"] == "MEDIUM")

    st.markdown("### 🧠 Actionable Insights")
    st.markdown(
        f"<small style='color:#4a6070;'>"
        f"{high_count} critical &nbsp;·&nbsp; {medium_count} medium &nbsp;·&nbsp; "
        f"Based on live audit results"
        f"</small>",
        unsafe_allow_html=True
    )

    for ins in insights:
        sev_c  = _sev_color(ins["severity"])
        sev_bg = _sev_bg(ins["severity"])
        st.markdown(f"""
        <div style='
            background:{sev_bg};
            border:1px solid {sev_c}44;
            border-left:4px solid {sev_c};
            border-radius:8px;
            padding:0.9rem 1.2rem;
            margin-bottom:0.6rem;
        '>
            <div style='display:flex;align-items:center;gap:0.6rem;margin-bottom:0.3rem;'>
                <span style='font-size:1.1rem;'>{ins['icon']}</span>
                <span style='
                    font-family:"IBM Plex Mono",monospace;
                    font-size:0.88rem;
                    font-weight:600;
                    color:#dce8f0;
                '>{ins['title']}</span>
                <span style='
                    margin-left:auto;
                    font-family:"IBM Plex Mono",monospace;
                    font-size:0.7rem;
                    color:{sev_c};
                    border:1px solid {sev_c};
                    padding:1px 8px;
                    border-radius:4px;
                '>{ins['severity']}</span>
            </div>
            <div style='font-size:0.84rem;color:#c9d1d9;margin-bottom:0.25rem;'>{ins['body']}</div>
            <div style='font-size:0.78rem;color:#4a6070;'>
                <strong style='color:#6e7681;'>Impact:</strong> {ins['impact']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    g_col, _ = st.columns([1, 3])

    with g_col:
        score = report["health_score"]
        grade = report["health_grade"]
        st.plotly_chart(make_gauge(score), use_container_width=True)
        st.markdown(
            f"<div style='text-align:center;font-family:\"IBM Plex Mono\",monospace;"
            f"font-size:1.1rem;color:{_score_color(score)};'>Grade {grade}</div>",
            unsafe_allow_html=True
        )




# ─────────────────────────────────────────────
# TAB 2 — BILL OF HEALTH
# ─────────────────────────────────────────────
with tab2:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:1.8rem;font-weight:800;"
        "color:#dce8f0;letter-spacing:-0.02em;margin-bottom:0.2rem;'>Bill of Health</div>"
        "<div style='width:60px;height:2px;background:#00e5a0;margin-bottom:0.6rem;'></div>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<small style='color:#4a6070;'>Scanned at {report['scanned_at']} &nbsp;|&nbsp; "
        f"File: <code>{report['file']}</code></small>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    for key, check in checks.items():
        sev  = check.get("severity", "OK")
        icon = {"HIGH": "🔴", "MEDIUM": "🟡", "OK": "🟢"}[sev]
        cat  = {"A": "AUTO-FIX", "M": "MANUAL", "I": "INFO"}.get(check.get("category","I"), "INFO")

        with st.expander(f"{icon}  {check['label']}  —  [{sev}]", expanded=(sev == "HIGH")):
            # render the coloured badge inside where HTML is supported
            st.markdown(_badge(sev), unsafe_allow_html=True)
            col_a, col_b = st.columns([3, 1])
            with col_a:
                if check.get("found"):
                    st.markdown(f"**Suggestion:** {check.get('suggestion','')}")
                    if check.get("alt_fix"):
                        st.markdown(f"_Alt fix: `{check['alt_fix']}`_")
                    if check.get("manual_fixes"):
                        st.markdown(f"_Manual options: `{'`, `'.join(check['manual_fixes'])}`_")

                    # ── per-check detail ──
                    if key == "nulls" and "by_column" in check:
                        st.dataframe(
                            pd.DataFrame(check["by_column"]).T.rename(
                                columns={"count":"Null Count","pct":"Null %"}
                            ),
                            use_container_width=True
                        )
                    elif key == "outliers" and "by_column" in check:
                        st.dataframe(
                            pd.DataFrame(check["by_column"]).T,
                            use_container_width=True
                        )
                    elif key == "high_correlation" and check.get("pairs"):
                        st.dataframe(
                            pd.DataFrame(check["pairs"]),
                            use_container_width=True
                        )
                    elif key == "typos" and "by_column" in check:
                        for col_name, groups in check["by_column"].items():
                            st.markdown(f"**{col_name}**: " + "  |  ".join(str(g) for g in groups[:5]))
                    elif "by_column" in check and isinstance(check["by_column"], dict):
                        st.json(check["by_column"])
                else:
                    st.success("No issues found ✓")
            with col_b:
                st.markdown(f"`{cat}`")
                if check.get("fix_key"):
                    st.markdown(f"fix: `{check['fix_key']}`")


# ─────────────────────────────────────────────
# TAB 3 — SMART CLEAN
# ─────────────────────────────────────────────
with tab3:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:1.8rem;font-weight:800;"
        "color:#dce8f0;letter-spacing:-0.02em;margin-bottom:0.2rem;'>Smart Clean</div>"
        "<div style='width:60px;height:2px;background:#00e5a0;margin-bottom:0.6rem;'></div>",
        unsafe_allow_html=True
    )
    st.markdown("<small style='color:#4a6070;'>Select which fixes to apply, then click Run.</small>", unsafe_allow_html=True)
    st.markdown("---")

    permissions = {}
    any_fixable = False

    for key, check in checks.items():
        if not check.get("fix_key"):
            continue
        sev      = check.get("severity", "OK")
        found    = check.get("found", False)
        icon     = {"HIGH": "🔴", "MEDIUM": "🟡", "OK": "🟢"}[sev]
        default  = found and sev in ("HIGH", "MEDIUM")
        disabled = not found

        permissions[key] = st.checkbox(
            f"{icon}  {check['label']}",
            value=default,
            disabled=disabled,
            help=check.get("suggestion", ""),
            key=f"perm_{key}",
        )
        if found:
            any_fixable = True

    st.markdown("---")

    clean_btn = st.button("🧹  Apply Selected Fixes", use_container_width=True, disabled=not any_fixable)

    if clean_btn:
        with st.spinner("Cleaning in progress…"):
            try:
                from data_auditor_v4 import DataCleaner  # type: ignore

                cleaner = DataCleaner(_tmp_path, audit_report=report)

                # ── FIX: replace the freshly-loaded df with the auditor's df
                # so both objects work on the exact same data state.
                # Without this, DataCleaner reloads from file and any
                # in-memory state from the audit session is lost.
                if hasattr(st.session_state, "auditor") and \
                   st.session_state.get("auditor") is not None:
                    cleaner.df          = st.session_state.auditor.df.copy()
                    cleaner.original_df = cleaner.df.copy()
                    cleaner.stats_before = cleaner._stats()

                # skew_threshold passed directly to run() → smart_impute()
                cleaner.run(permissions, skew_threshold=skew_threshold)

                st.session_state.clean_df      = cleaner.df.copy()
                st.session_state.audit_log     = cleaner.get_audit_log()
                st.session_state.clean_summary = cleaner.diff_report()
            except Exception as e:
                st.error(f"Cleaning failed: {e}")

    if st.session_state.clean_df is not None:
        diff    = st.session_state.clean_summary
        clean_df= st.session_state.clean_df

        st.markdown("### ✅ Cleaning Complete")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Rows removed",  diff["rows_removed"])
        d2.metric("Cols removed",  diff["cols_removed"])
        d3.metric("Nulls fixed",   diff["nulls_fixed"])
        d4.metric("Duplicates removed", diff["duplicates_removed"])

        st.markdown("#### Operations Log")
        for entry in st.session_state.audit_log:
            st.markdown(f"`{entry}`")

        st.markdown("#### Preview — Cleaned Data")
        st.dataframe(clean_df.head(20), use_container_width=True)

        st.markdown("---")
        st.markdown("#### 💾 Download")
        dl1, dl2 = st.columns(2)
        with dl1:
            csv_buf = io.StringIO()
            clean_df.to_csv(csv_buf, index=False)
            st.download_button(
                "Download CSV",
                data=csv_buf.getvalue(),
                file_name="cleaned_data.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with dl2:
            xl_buf = io.BytesIO()
            clean_df.to_excel(xl_buf, index=False, engine="openpyxl")
            xl_buf.seek(0)
            st.download_button(
                "Download Excel",
                data=xl_buf.getvalue(),
                file_name="cleaned_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


# ─────────────────────────────────────────────
# TAB 4 — PRIVACY & SECURITY
# ─────────────────────────────────────────────
with tab4:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:1.8rem;font-weight:800;"
        "color:#dce8f0;letter-spacing:-0.02em;margin-bottom:0.2rem;'>Privacy & Security</div>"
        "<div style='width:60px;height:2px;background:#00e5a0;margin-bottom:0.6rem;'></div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<small style='color:#4a6070;'>Mask or hash sensitive columns before sharing data externally. "
        "Uses <code>mask_pii()</code> and <code>hash_column()</code> from the DataCleaner.</small>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── detect PII from audit ─────────────────
    pii_check      = checks.get("pii", {})
    pii_cols_audit = pii_check.get("columns", [])

    # Work on the same df we'll actually transform —
    # cleaned df if available (column names may have changed), else raw
    src_df   = (
        st.session_state.clean_df.copy()
        if st.session_state.clean_df is not None
        else df_raw.copy()
    )
    all_cols = src_df.columns.tolist()

    # FIX: build a bidirectional lookup so we match PII columns
    # whether the df has been cleaned (snake_case) or not (original names).
    # Strategy: for every actual column, store both its original name AND
    # its snake_case equivalent as keys pointing to the actual column name.
    import re as _re
    def _to_snake(name):
        return _re.sub(r'\W+', '_', str(name)).strip('_').lower()

    # col_lookup: any variant → actual column name in src_df
    col_lookup = {}
    for c in all_cols:
        col_lookup[c]            = c          # exact match
        col_lookup[_to_snake(c)] = c          # snake of actual → actual

    def _resolve(audit_col):
        """Return the actual column name in src_df, or None if not found."""
        if audit_col in col_lookup:
            return col_lookup[audit_col]
        snake = _to_snake(audit_col)
        return col_lookup.get(snake)

    pii_cols_translated = list(dict.fromkeys(
        r for r in (_resolve(c) for c in pii_cols_audit) if r is not None
    ))

    # User can also add extra columns manually
    st.markdown("### 🔍 Detected Sensitive Columns")
    if pii_cols_audit:
        st.markdown(
            "The auditor flagged the following columns as potentially containing personal data:"
        )
        for c in pii_cols_translated:
            st.markdown(
                f"<span style='background:#3d1010;border:1px solid #da363344;"
                f"border-radius:4px;padding:2px 10px;font-family:\"IBM Plex Mono\",monospace;"
                f"font-size:.82rem;color:#ff7b72;'>{c}</span> &nbsp;",
                unsafe_allow_html=True
            )
        st.markdown("")
    else:
        st.info("No PII columns auto-detected. You can still select columns manually below.")

    st.markdown("---")
    st.markdown("### ⚙️ Configure Masking")

    # ── column selector ───────────────────────
    cols_to_mask = st.multiselect(
        "Columns to mask (partial — shows first 2 and last 2 chars)",
        options=all_cols,
        default=[c for c in pii_cols_translated if c in all_cols],
        key="mask_cols",
    )
    cols_to_hash = st.multiselect(
        "Columns to hash (SHA-256 — irreversible, good for IDs & passwords)",
        options=all_cols,
        default=[],
        key="hash_cols",
    )

    hash_algo = st.radio(
        "Hash algorithm",
        options=["sha256", "md5"],
        horizontal=True,
        help="SHA-256 is recommended. MD5 is faster but weaker.",
    )

    st.markdown("---")

    privacy_btn = st.button(
        "🔒  Apply Privacy Transformations",
        use_container_width=True,
        disabled=(not cols_to_mask and not cols_to_hash),
    )

    if privacy_btn:
        with st.spinner("Applying privacy transformations…"):
            try:
                from data_auditor_v4 import DataCleaner  # type: ignore

                # FIX: inject src_df directly — no temp file round-trip needed.
                # This guarantees the cleaner operates on the exact same columns
                # the user sees in the multiselect above.
                priv_cleaner             = DataCleaner(_tmp_path, audit_report=report)
                priv_cleaner.df          = src_df.copy()
                priv_cleaner.original_df = priv_cleaner.df.copy()

                if cols_to_mask:
                    priv_cleaner.mask_pii(cols_to_mask)
                if cols_to_hash:
                    for hcol in cols_to_hash:
                        priv_cleaner.hash_column(hcol, algorithm=hash_algo)

                st.session_state.privacy_df  = priv_cleaner.df.copy()
                st.session_state.privacy_log = priv_cleaner.get_audit_log()

            except Exception as e:
                st.error(f"Privacy transformation failed: {e}")

    # ── show result ───────────────────────────
    if "privacy_df" in st.session_state and st.session_state.privacy_df is not None:
        priv_df = st.session_state.privacy_df

        st.markdown("### ✅ Transformation Complete")
        st.markdown("#### Operations Applied")
        for entry in st.session_state.get("privacy_log", []):
            st.markdown(f"`{entry}`")

        st.markdown("#### Preview")
        st.dataframe(priv_df.head(20), use_container_width=True)

        st.markdown("---")
        st.markdown("#### 💾 Download Privacy-Safe File")
        pv1, pv2 = st.columns(2)
        with pv1:
            csv_priv = io.StringIO()
            priv_df.to_csv(csv_priv, index=False)
            st.download_button(
                "Download CSV (masked)",
                data=csv_priv.getvalue(),
                file_name="privacy_safe_data.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with pv2:
            xl_priv = io.BytesIO()
            priv_df.to_excel(xl_priv, index=False, engine="openpyxl")
            xl_priv.seek(0)
            st.download_button(
                "Download Excel (masked)",
                data=xl_priv.getvalue(),
                file_name="privacy_safe_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # ── side-by-side diff for one column ──
        if cols_to_mask or cols_to_hash:
            changed_cols = list(set(cols_to_mask + cols_to_hash))
            preview_col  = st.selectbox(
                "Compare before / after for column",
                options=changed_cols,
                key="priv_preview_col",
            )
            before_vals = src_df[preview_col].astype(str).head(8).tolist()
            after_vals  = priv_df[preview_col].astype(str).head(8).tolist()
            diff_df = pd.DataFrame({
                "Original": before_vals,
                "After masking / hashing": after_vals,
            })
            st.dataframe(diff_df, use_container_width=True)




# ─────────────────────────────────────────────
# TAB 5 — SMART SQL SCHEMA GENERATOR
# ─────────────────────────────────────────────
with tab5:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:1.8rem;font-weight:800;"
        "color:#dce8f0;letter-spacing:-0.02em;margin-bottom:0.2rem;'>Smart SQL Schema</div>"
        "<div style='width:60px;height:2px;background:#00e5a0;margin-bottom:0.4rem;'></div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<small style='color:#4a6070;'>"
        "Generates an optimized <code>CREATE TABLE</code> script — sized VARCHARs, "
        "correct integer ranges, auto Primary Key detection. "
        "Run <b>Smart Clean</b> first for the most accurate types."
        "</small>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    sql_src_df  = st.session_state.clean_df if st.session_state.clean_df is not None else df_raw
    src_label   = "✅ Cleaned data" if st.session_state.clean_df is not None else "⚠️ Raw data"

    st.markdown(
        f"<small style='color:#4a6070;'>Source: {src_label} &nbsp;|&nbsp; "
        f"{len(sql_src_df):,} rows × {len(sql_src_df.columns)} cols</small>",
        unsafe_allow_html=True
    )
    st.markdown("")

    # ── Settings row ──────────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns([2, 2, 2, 2])
    with sc1:
        default_table = uploaded_file.name.rsplit(".", 1)[0].lower().replace(" ","_").replace("-","_")
        table_name    = st.text_input("Table name", value=default_table, key="sql_table")
    with sc2:
        schema_name = st.text_input("Schema (optional)", value="", placeholder="e.g. dbo", key="sql_schema")
    with sc3:
        dialect = st.selectbox(
            "Target dialect",
            ["postgresql", "mysql", "sqlserver"],
            format_func=lambda x: {"postgresql":"PostgreSQL","mysql":"MySQL","sqlserver":"SQL Server"}[x],
            key="sql_dialect"
        )
    with sc4:
        detected_pk = _detect_primary_key(sql_src_df)
        pk_options  = ["(auto-detect)"] + sql_src_df.columns.tolist()
        pk_default  = pk_options.index(detected_pk) if detected_pk and detected_pk in pk_options else 0
        pk_choice   = st.selectbox("Primary Key", pk_options, index=pk_default, key="sql_pk")
        pk_col      = None if pk_choice == "(auto-detect)" else pk_choice

    # ── Column Type Map (editable overview) ───────────────────
    st.markdown("---")
    st.markdown(
        "<span style='font-family:\"JetBrains Mono\",monospace;font-size:.7rem;"
        "color:var(--accent);letter-spacing:.15em;text-transform:uppercase;'>◈ Smart Type Mapping</span>",
        unsafe_allow_html=True
    )
    st.markdown("")

    type_rows = []
    auto_pk   = pk_col or _detect_primary_key(sql_src_df)
    for col in sql_src_df.columns:
        s        = sql_src_df[col]
        sql_type = _sql_type_for(s, dialect)
        nulls    = int(s.isnull().sum())
        unique   = int(s.nunique())
        is_pk    = col == auto_pk
        type_rows.append({
            "Column":       col,
            "Pandas dtype": str(s.dtype),
            "SQL type":     sql_type,
            "Nulls":        nulls,
            "Unique":       unique,
            "NOT NULL":     "✅" if nulls == 0 else "—",
            "PK":           "🔑" if is_pk else "",
        })

    type_df = pd.DataFrame(type_rows)

    # highlight PK row
    def _highlight_pk(row):
        if row["PK"] == "🔑":
            return ["background-color:#061a10;color:#00e5a0"] * len(row)
        return [""] * len(row)

    st.dataframe(
        type_df.style.apply(_highlight_pk, axis=1),
        use_container_width=True,
        height=min(40 + len(type_rows) * 35, 480),
    )

    if auto_pk:
        st.markdown(
            f"<small style='color:var(--accent);'>🔑 Auto-detected Primary Key: <b>{auto_pk}</b> "
            f"({sql_src_df[auto_pk].nunique():,} unique, 0 nulls)</small>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<small style='color:#4a6070;'>No column qualified for auto Primary Key "
            "(needs unique values, zero nulls, and an ID-like name).</small>",
            unsafe_allow_html=True
        )

    # ── Generate script ───────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<span style='font-family:\"JetBrains Mono\",monospace;font-size:.7rem;"
        "color:var(--accent);letter-spacing:.15em;text-transform:uppercase;'>◈ Generated Script</span>",
        unsafe_allow_html=True
    )
    st.markdown("")

    sql = generate_sql_schema(
        sql_src_df,
        table_name=table_name,
        dialect=dialect,
        schema=schema_name,
        pk_col=pk_col,
    )
    st.code(sql, language="sql")

    # ── Tip box ───────────────────────────────────────────────
    varchar_count = sum(1 for r in type_rows if "VARCHAR" in r["SQL type"])
    tinyint_count = sum(1 for r in type_rows if r["SQL type"] == "TINYINT")
    decimal_count = sum(1 for r in type_rows if "DECIMAL" in r["SQL type"])

    tips = []
    if varchar_count:
        tips.append(f"**{varchar_count} VARCHAR columns** sized by actual data (not lazy TEXT) — saves disk & speeds up string indexes.")
    if tinyint_count:
        tips.append(f"**{tinyint_count} TINYINT column(s)** detected — uses 1 byte instead of 4 (INT), ideal for flags and small codes.")
    if decimal_count:
        tips.append(f"**{decimal_count} DECIMAL(18,2) column(s)** — fixed precision, safe for money and metrics (no floating point drift).")
    if auto_pk:
        tips.append(f"**PRIMARY KEY on `{auto_pk}`** — the database will auto-create a clustered index on this column.")

    if tips:
        st.markdown("")
        st.info("💡 **Smart Mapping Notes:**\n\n" + "\n\n".join(f"- {t}" for t in tips))

    # ── Downloads ─────────────────────────────────────────────
    st.markdown("---")
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇  Download SQL Script (.sql)",
            data=sql,
            file_name=f"{table_name}_schema.sql",
            mime="text/plain",
            use_container_width=True,
        )
    with dl2:
        # also export the type map as CSV
        st.download_button(
            "⬇  Download Type Map (.csv)",
            data=type_df.to_csv(index=False),
            file_name=f"{table_name}_type_map.csv",
            mime="text/csv",
            use_container_width=True,
        )





# ─────────────────────────────────────────────
# TAB 6 — DASHBOARD
# ─────────────────────────────────────────────
with tab6:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:1.8rem;font-weight:800;"
        "color:#dce8f0;letter-spacing:-0.02em;margin-bottom:0.2rem;'>Dashboard</div>"
        "<div style='width:60px;height:2px;background:#00e5a0;margin-bottom:0.4rem;'></div>",
        unsafe_allow_html=True
    )

    # ── shared data source ────────────────────────────────────
    dash_df    = st.session_state.clean_df.copy() if st.session_state.clean_df is not None else df_raw.copy()
    dash_label = "✅ Cleaned" if st.session_state.clean_df is not None else "⚠️ Raw"
    st.markdown(
        f"<small style='color:#4a6070;'>Source: {dash_label} &nbsp;|&nbsp; "
        f"{len(dash_df):,} rows × {len(dash_df.columns)} cols</small>",
        unsafe_allow_html=True
    )

    num_cols      = dash_df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols      = dash_df.select_dtypes(include=["object", "category"]).columns.tolist()
    all_dash_cols = dash_df.columns.tolist()

    # ── shared plotly themes ──────────────────────────────────
    _DL  = dict(template="plotly_dark")
    _DLL = dict(
        template="plotly_dark",
        paper_bgcolor="#060809",
        plot_bgcolor="#0c1014",
        font=dict(family="JetBrains Mono, monospace", color="#dce8f0", size=11),
    )

    # ── global accent color picker (sidebar of dashboard) ─────
    accent_color = st.color_picker("🎨 Accent color", "#00e5a0", key="dash_accent")
    color_seq    = [accent_color, "#00b87a", "#ffb347", "#ff4444", "#7eb8f7", "#c084fc"]

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # INNER TABS
    # ══════════════════════════════════════════════════════════
    d_tab1, d_tab2, d_tab3, d_tab4, d_tab5, d_tab6, d_tab7 = st.tabs([
        "🔍  Explorer",
        "📊  Distribution",
        "🔗  Correlation",
        "📦  Outliers",
        "🚫  Missing",
        "🏷️  Top Values",
        "🏥  Quality",
    ])

    # ─────────────────────────────────────────
    # D-TAB 1 — EXPLORER (custom chart builder)
    # ─────────────────────────────────────────
    with d_tab1:
        st.markdown("#### 🔍 Chart Explorer")
        st.markdown("<small style='color:#4a6070;'>Build any chart — choose columns, type, and filter.</small>", unsafe_allow_html=True)
        st.markdown("")

        # controls
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            chart_type = st.selectbox("Chart type", ["Histogram","Bar","Line","Scatter","Box","Violin","Area"], key="exp_type")
        with c2:
            x_col = st.selectbox("X axis", all_dash_cols, key="exp_x")
        with c3:
            y_col = st.selectbox("Y axis (optional)", ["(none)"] + num_cols, key="exp_y")
            y_col = None if y_col == "(none)" else y_col
        with c4:
            color_col = st.selectbox("Color / Group", ["(none)"] + cat_cols, key="exp_color")
            color_col = None if color_col == "(none)" else color_col

        c5, c6, c7 = st.columns(3)
        with c5:
            nbins    = st.slider("Bins", 5, 100, 30, key="exp_bins")
        with c6:
            _max_slider = max(100, len(dash_df))
            _def_slider = min(5000, len(dash_df))
            max_rows = st.slider("Max rows", 100, _max_slider, _def_slider, 100, key="exp_rows") if len(dash_df) > 100 else len(dash_df)
        with c7:
            top_n = st.slider("Top N (bar)", 5, 50, 15, key="exp_topn")

        # filter row
        st.markdown("**Filter**")
        f1, f2, f3 = st.columns([2, 1, 3])
        with f1:
            fcol = st.selectbox("Column", ["(none)"] + all_dash_cols, key="exp_fcol")
        with f2:
            fop  = st.selectbox("Op", ["==","!=",">","<",">=","<=","contains"], key="exp_fop")
        with f3:
            fval = st.text_input("Value", "", key="exp_fval")

        plot_df = dash_df.head(max_rows).copy()
        if fcol != "(none)" and fval.strip():
            try:
                s = plot_df[fcol]
                v = fval.strip()
                if fop == "==":         plot_df = plot_df[s.astype(str) == v]
                elif fop == "!=":       plot_df = plot_df[s.astype(str) != v]
                elif fop == "contains": plot_df = plot_df[s.astype(str).str.contains(v, case=False, na=False)]
                else:
                    nv = float(v)
                    ops = {">": s.__gt__, "<": s.__lt__, ">=": s.__ge__, "<=": s.__le__}
                    plot_df = plot_df[ops[fop](nv)]
                st.markdown(f"<small style='color:{accent_color};'>▸ {len(plot_df):,} rows after filter</small>", unsafe_allow_html=True)
            except Exception as fe:
                st.markdown(f"<small style='color:#ffb347;'>Filter error: {fe}</small>", unsafe_allow_html=True)

        # build chart
        try:
            fig = None
            if chart_type == "Histogram":
                fig = px.histogram(plot_df, x=x_col, nbins=nbins, color=color_col,
                                   color_discrete_sequence=color_seq, title=f"Distribution — {x_col}", **_DL)
            elif chart_type == "Bar":
                if y_col:
                    fig = px.bar(plot_df, x=x_col, y=y_col, color=color_col,
                                 color_discrete_sequence=color_seq, title=f"{y_col} by {x_col}", **_DL)
                else:
                    vc = plot_df[x_col].value_counts().head(top_n)
                    fig = px.bar(x=vc.index, y=vc.values, labels={"x":x_col,"y":"Count"},
                                 color=vc.values, color_continuous_scale=[[0,"#0c1014"],[1,accent_color]],
                                 title=f"Top {top_n} — {x_col}", **_DL)
                    fig.update_layout(coloraxis_showscale=False)
            elif chart_type == "Line":
                if y_col:
                    fig = px.line(plot_df, x=x_col, y=y_col, color=color_col,
                                  color_discrete_sequence=color_seq, title=f"{y_col} over {x_col}", **_DL)
            elif chart_type == "Scatter":
                if y_col:
                    fig = px.scatter(plot_df, x=x_col, y=y_col, color=color_col,
                                     color_discrete_sequence=color_seq, opacity=0.65,
                                     title=f"{x_col} vs {y_col}", **_DL)
            elif chart_type == "Box":
                yb = x_col if x_col in num_cols else (num_cols[0] if num_cols else x_col)
                fig = px.box(plot_df, x=color_col, y=yb, color=color_col,
                             color_discrete_sequence=color_seq, title=f"Box — {yb}", **_DL)
            elif chart_type == "Violin":
                yv = x_col if x_col in num_cols else (num_cols[0] if num_cols else x_col)
                fig = px.violin(plot_df, x=color_col, y=yv, color=color_col,
                                color_discrete_sequence=color_seq, box=True,
                                title=f"Violin — {yv}", **_DL)
            elif chart_type == "Area":
                if y_col:
                    fig = px.area(plot_df, x=x_col, y=y_col, color=color_col,
                                  color_discrete_sequence=color_seq,
                                  title=f"{y_col} area over {x_col}", **_DL)

            if fig:
                fig.update_layout(height=460, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Select a Y axis column to draw this chart type.")
        except Exception as ce:
            st.error(f"Chart error: {ce}")

        st.markdown("---")
        prev_n = st.slider("Preview rows", 5, 200, 30, key="exp_prev")
        st.dataframe(plot_df.head(prev_n), use_container_width=True, height=280)
        st.download_button("⬇ Download filtered CSV", plot_df.to_csv(index=False).encode(),
                           "filtered_data.csv", "text/csv")

    # ─────────────────────────────────────────
    # D-TAB 2 — DISTRIBUTION
    # ─────────────────────────────────────────
    with d_tab2:
        st.markdown("#### 📊 Distribution Explorer")
        if not num_cols:
            st.info("No numeric columns found.")
        else:
            d1, d2, d3 = st.columns(3)
            with d1:
                dist_col  = st.selectbox("Column", num_cols, key="dist_col2")
            with d2:
                dist_bins = st.slider("Bins", 5, 100, 30, key="dist_bins2")
            with d3:
                dist_marg = st.selectbox("Marginal", ["box","violin","rug","none"], key="dist_marg")
                dist_marg = None if dist_marg == "none" else dist_marg

            grp_col = st.selectbox("Split by (optional)", ["(none)"] + cat_cols, key="dist_grp")
            grp_col = None if grp_col == "(none)" else grp_col

            fig_dist = px.histogram(
                dash_df, x=dist_col, nbins=dist_bins,
                color=grp_col,
                color_discrete_sequence=color_seq,
                marginal=dist_marg,
                title=f"Distribution — {dist_col}",
                **_DL
            )
            fig_dist.update_layout(height=420, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
            st.plotly_chart(fig_dist, use_container_width=True)

            # stats card
            s = dash_df[dist_col].dropna()
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            sc1.metric("Mean",   f"{s.mean():.3f}")
            sc2.metric("Median", f"{s.median():.3f}")
            sc3.metric("Std",    f"{s.std():.3f}")
            sc4.metric("Skew",   f"{s.skew():.3f}")
            sc5.metric("Nulls",  int(dash_df[dist_col].isnull().sum()))

    # ─────────────────────────────────────────
    # D-TAB 3 — CORRELATION
    # ─────────────────────────────────────────
    with d_tab3:
        st.markdown("#### 🔗 Correlation Heatmap")
        if len(num_cols) < 2:
            st.info("Need ≥ 2 numeric columns.")
        else:
            sel_corr = st.multiselect("Columns to include", num_cols, default=num_cols[:min(10,len(num_cols))], key="corr_sel")
            corr_method = st.radio("Method", ["pearson","spearman","kendall"], horizontal=True, key="corr_method")

            if len(sel_corr) >= 2:
                corr_mx = dash_df[sel_corr].corr(method=corr_method)
                fig_corr = px.imshow(
                    corr_mx, text_auto=".2f",
                    color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1,
                    title=f"Correlation Matrix ({corr_method})",
                    **_DL
                )
                fig_corr.update_layout(height=480, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
                st.plotly_chart(fig_corr, use_container_width=True)

                # top correlated pairs
                mask  = np.triu(np.ones(corr_mx.shape), k=1).astype(bool)
                pairs = (corr_mx.where(mask).stack()
                         .reset_index()
                         .rename(columns={"level_0":"Col A","level_1":"Col B",0:"r"})
                         .assign(abs_r=lambda d: d["r"].abs())
                         .sort_values("abs_r", ascending=False)
                         .drop(columns="abs_r")
                         .reset_index(drop=True))
                st.markdown("**Top correlated pairs**")
                st.dataframe(pairs.head(10), use_container_width=True, height=280)
            else:
                st.info("Select at least 2 columns.")

    # ─────────────────────────────────────────
    # D-TAB 4 — OUTLIERS
    # ─────────────────────────────────────────
    with d_tab4:
        st.markdown("#### 📦 Outlier Analysis")
        if not num_cols:
            st.info("No numeric columns.")
        else:
            o1, o2 = st.columns(2)
            with o1:
                out_cols = st.multiselect("Columns", num_cols, default=num_cols[:min(4,len(num_cols))], key="out_cols")
            with o2:
                out_type = st.radio("Plot type", ["Box","Violin"], horizontal=True, key="out_type")

            if out_cols:
                if out_type == "Box":
                    fig_out = go.Figure()
                    for i, col in enumerate(out_cols):
                        fig_out.add_trace(go.Box(
                            y=dash_df[col], name=col,
                            marker_color=color_seq[i % len(color_seq)],
                            boxmean="sd", line_width=1.5
                        ))
                else:
                    fig_out = go.Figure()
                    for i, col in enumerate(out_cols):
                        fig_out.add_trace(go.Violin(
                            y=dash_df[col], name=col,
                            line_color=color_seq[i % len(color_seq)],
                            fillcolor=color_seq[i % len(color_seq)] + "33",
                            box_visible=True, meanline_visible=True
                        ))
                fig_out.update_layout(height=420, margin=dict(t=20,b=20,l=20,r=20),
                                      showlegend=True, **_DLL)
                st.plotly_chart(fig_out, use_container_width=True)

                # outlier stats table
                rows = []
                for col in out_cols:
                    s  = dash_df[col].dropna().astype(float)
                    if s.empty:
                        continue
                    q1, q3 = s.quantile(.25), s.quantile(.75)
                    iqr = q3 - q1
                    n_out = int(((s < q1-1.5*iqr) | (s > q3+1.5*iqr)).sum())
                    rows.append({"Column":col, "Min":round(s.min(),3), "Max":round(s.max(),3),
                                 "Mean":round(s.mean(),3), "Std":round(s.std(),3),
                                 "IQR":round(iqr,3), "Outliers (IQR)":n_out})
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.info("Select at least one column.")

    # ─────────────────────────────────────────
    # D-TAB 5 — MISSING VALUES
    # ─────────────────────────────────────────
    with d_tab5:
        st.markdown("#### 🚫 Missing Values Map")
        null_df = pd.DataFrame({
            "Column":    dash_df.columns,
            "Missing":   dash_df.isnull().sum().values,
            "Missing %": (dash_df.isnull().mean() * 100).round(2).values,
            "Present":   dash_df.notnull().sum().values,
        }).sort_values("Missing %", ascending=False)

        has_nulls = null_df[null_df["Missing"] > 0]

        if has_nulls.empty:
            st.success("🎉 Zero missing values in this dataset!")
        else:
            m1, m2 = st.columns(2)
            with m1:
                fig_null_h = px.bar(
                    has_nulls, x="Missing %", y="Column", orientation="h",
                    color="Missing %",
                    color_continuous_scale=[[0,"#1c2a35"],[0.5,"#ffb347"],[1,"#ff4444"]],
                    title="Missing % per Column",
                    **_DL
                )
                fig_null_h.update_layout(height=380, margin=dict(t=40,b=10,l=10,r=10),
                                         coloraxis_showscale=False, **_DLL)
                st.plotly_chart(fig_null_h, use_container_width=True)
            with m2:
                # stacked present vs missing
                fig_stack = go.Figure()
                fig_stack.add_trace(go.Bar(
                    name="Present", y=null_df["Column"], x=null_df["Present"],
                    orientation="h", marker_color=accent_color, opacity=0.8
                ))
                fig_stack.add_trace(go.Bar(
                    name="Missing", y=null_df["Column"], x=null_df["Missing"],
                    orientation="h", marker_color="#ff4444", opacity=0.8
                ))
                fig_stack.update_layout(
                    barmode="stack", height=380, title="Present vs Missing",
                    margin=dict(t=40,b=10,l=10,r=10), **_DLL
                )
                st.plotly_chart(fig_stack, use_container_width=True)

            st.dataframe(null_df, use_container_width=True, height=220)

    # ─────────────────────────────────────────
    # D-TAB 6 — TOP VALUES
    # ─────────────────────────────────────────
    with d_tab6:
        st.markdown("#### 🏷️ Top Values Analysis")
        if not cat_cols:
            st.info("No categorical columns found.")
        else:
            tv1, tv2 = st.columns(2)
            with tv1:
                tv_col = st.selectbox("Column", cat_cols, key="tv_col2")
            with tv2:
                tv_n = st.slider("Top N", 3, 50, 15, key="tv_n2")

            grp_tv = st.selectbox("Compare by (optional)", ["(none)"] + cat_cols, key="tv_grp")
            grp_tv = None if grp_tv == "(none)" or grp_tv == tv_col else grp_tv

            if grp_tv:
                # grouped stacked bar
                grp_data = (dash_df.groupby([tv_col, grp_tv])
                            .size().reset_index(name="count"))
                top_vals  = dash_df[tv_col].value_counts().head(tv_n).index
                grp_data  = grp_data[grp_data[tv_col].isin(top_vals)]
                fig_tv = px.bar(grp_data, x=tv_col, y="count", color=grp_tv,
                                color_discrete_sequence=color_seq,
                                barmode="stack", title=f"Top {tv_n} {tv_col} by {grp_tv}",
                                **_DL)
            else:
                top = dash_df[tv_col].value_counts().head(tv_n)
                fig_tv = px.bar(
                    x=top.index, y=top.values,
                    labels={"x": tv_col, "y": "Count"},
                    color=top.values,
                    color_continuous_scale=[[0,"#0c1014"],[1,accent_color]],
                    title=f"Top {tv_n} — {tv_col}", **_DL
                )
                fig_tv.update_layout(coloraxis_showscale=False)

            fig_tv.update_layout(height=420, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
            st.plotly_chart(fig_tv, use_container_width=True)

            # pie chart
            top_pie = dash_df[tv_col].value_counts().head(tv_n)
            fig_pie = px.pie(values=top_pie.values, names=top_pie.index,
                             color_discrete_sequence=color_seq,
                             title=f"Share — {tv_col}", **_DL)
            fig_pie.update_layout(height=350, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
            st.plotly_chart(fig_pie, use_container_width=True)

    # ─────────────────────────────────────────
    # D-TAB 7 — QUALITY
    # ─────────────────────────────────────────
    with d_tab7:
        st.markdown("#### 🏥 Data Quality Score")

        score_before = report["health_score"]
        grade_before = report["health_grade"]
        grade_color  = {"A":accent_color,"B":"#7eb8f7","C":"#ffb347","D":"#ff4444"}.get(grade_before,"#dce8f0")

        if st.session_state.get("clean_summary"):
            cs           = st.session_state.clean_summary
            # FIX: diff_report() returns nested before/after dicts —
            # rows_removed etc are top-level keys but before/after are nested
            rows_b       = cs.get("before", {}).get("rows", 1)
            score_after  = min(100, score_before + max(0,
                               (cs.get("nulls_fixed", 0) + cs.get("rows_removed", 0)) // max(rows_b // 20, 1)))
            grade_after  = "A" if score_after>=90 else "B" if score_after>=75 else "C" if score_after>=55 else "D"
            ga_color     = {"A":accent_color,"B":"#7eb8f7","C":"#ffb347","D":"#ff4444"}.get(grade_after,"#dce8f0")

            q1, q2 = st.columns(2)
            with q1:
                fig_b = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=score_before,
                    title={"text":f"Before  ·  Grade {grade_before}","font":{"size":12,"color":"#4a6070"}},
                    number={"suffix":"%","font":{"size":40,"color":"#ff4444"}},
                    gauge={"axis":{"range":[0,100]},"bar":{"color":"#ff4444"},
                           "steps":[{"range":[0,55],"color":"#1a0808"},{"range":[55,75],"color":"#1a1008"},
                                    {"range":[75,100],"color":"#061a10"}]},
                ))
                fig_b.update_layout(height=280, margin=dict(t=50,b=10,l=20,r=20), **_DLL)
                st.plotly_chart(fig_b, use_container_width=True)

            with q2:
                fig_a = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=score_after,
                    title={"text":f"After  ·  Grade {grade_after}","font":{"size":12,"color":"#4a6070"}},
                    number={"suffix":"%","font":{"size":40,"color":ga_color}},
                    gauge={"axis":{"range":[0,100]},"bar":{"color":ga_color},
                           "steps":[{"range":[0,55],"color":"#1a0808"},{"range":[55,75],"color":"#1a1008"},
                                    {"range":[75,100],"color":"#061a10"}]},
                ))
                fig_a.update_layout(height=280, margin=dict(t=50,b=10,l=20,r=20), **_DLL)
                st.plotly_chart(fig_a, use_container_width=True)

            # improvement summary
            delta = score_after - score_before
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Score Δ",       f"+{delta} pts",    delta_color="normal")
            m2.metric("Rows removed",  cs["rows_removed"])
            m3.metric("Cols removed",  cs["cols_removed"])
            m4.metric("Nulls fixed",   cs["nulls_fixed"])

            st.markdown("---")
            # issues breakdown bar
            sev_counts = {"HIGH":0,"MEDIUM":0,"OK":0}
            for c in checks.values():
                sev_counts[c.get("severity","OK")] += 1
            fig_sev = px.bar(
                x=list(sev_counts.keys()), y=list(sev_counts.values()),
                color=list(sev_counts.keys()),
                color_discrete_map={"HIGH":"#ff4444","MEDIUM":"#ffb347","OK":accent_color},
                labels={"x":"Severity","y":"Checks"},
                title="Audit Checks by Severity",
                **_DL
            )
            fig_sev.update_layout(height=280, showlegend=False,
                                  margin=dict(t=40,b=20,l=20,r=20), **_DLL)
            st.plotly_chart(fig_sev, use_container_width=True)

        else:
            # single gauge + issues breakdown
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score_before,
                title={"text":f"Health Score  ·  Grade {grade_before}",
                       "font":{"family":"JetBrains Mono","size":13,"color":"#4a6070"}},
                number={"suffix":"%","font":{"size":48,"color":grade_color}},
                gauge={
                    "axis":{"range":[0,100],"tickcolor":"#1c2a35"},
                    "bar":{"color":grade_color,"thickness":0.25},
                    "threshold":{"line":{"color":"#dce8f0","width":2},"thickness":0.75,"value":75},
                    "steps":[{"range":[0,55],"color":"#1a0808"},{"range":[55,75],"color":"#1a1008"},
                             {"range":[75,90],"color":"#0a1408"},{"range":[90,100],"color":"#061a10"}],
                },
            ))
            fig_g.update_layout(height=350, margin=dict(t=60,b=20,l=30,r=30), **_DLL)
            st.plotly_chart(fig_g, use_container_width=True)

            sev_counts = {"HIGH":0,"MEDIUM":0,"OK":0}
            for c in checks.values():
                sev_counts[c.get("severity","OK")] += 1

            qc1, qc2, qc3 = st.columns(3)
            qc1.metric("🔴 HIGH",   sev_counts["HIGH"])
            qc2.metric("🟡 MEDIUM", sev_counts["MEDIUM"])
            qc3.metric("🟢 OK",     sev_counts["OK"])

            st.markdown("")
            st.info("Run **Smart Clean** to unlock the Before vs After comparison.")

            # issues detail
            st.markdown("**Issues breakdown**")
            issues_rows = [
                {"Check": v["label"], "Severity": v.get("severity","OK"),
                 "Found": "✅" if v.get("found") else "—",
                 "Suggestion": v.get("suggestion","")[:80]}
                for v in checks.values() if v.get("found")
            ]
            if issues_rows:
                st.dataframe(pd.DataFrame(issues_rows), use_container_width=True, height=300)


st.markdown(
    "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;"
    "color:#1c2a35;letter-spacing:0.15em;text-align:center;padding:1rem 0;'>"
    "DATA INTELLIGENCE ENGINE &nbsp;·&nbsp; POWERED BY DATAAUDITOR v4"
    "</div>",
    unsafe_allow_html=True
)
