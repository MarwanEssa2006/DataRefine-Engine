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

/* ══ KILL ALL LINK/ANCHOR STYLING IN MARKDOWN CARDS ════════ */
/* Streamlit wraps text in <a> tags inside st.markdown —     */
/* this nukes all of that so card titles stay white           */
.stMarkdown a,
.stMarkdown a:link,
.stMarkdown a:visited,
.stMarkdown a:hover,
.stMarkdown a:active {
    color: inherit !important;
    text-decoration: none !important;
    background: none !important;
    border-bottom: none !important;
    font-style: normal !important;
}
div[data-testid="stMarkdownContainer"] a,
div[data-testid="stMarkdownContainer"] a:hover,
div[data-testid="stMarkdownContainer"] a * {
    color: inherit !important;
    text-decoration: none !important;
    border-bottom: none !important;
}
div[data-testid="stMarkdownContainer"] span,
div[data-testid="stMarkdownContainer"] div,
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] b,
div[data-testid="stMarkdownContainer"] strong {
    text-decoration: none !important;
    border-bottom: none !important;
    font-style: normal !important;
}
/* Card titles — force Syne display font, never italic, never monospace */
div[data-testid="stMarkdownContainer"] [style*="font-weight:800"],
div[data-testid="stMarkdownContainer"] [style*="font-weight: 800"] {
    font-family: 'Syne', sans-serif !important;
    font-style: normal !important;
    font-weight: 800 !important;
    text-decoration: none !important;
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
/* Kill Streamlit's default sliding red/brand-color highlight bar */
div[data-baseweb="tab-highlight"] {
    background-color: transparent !important;
    display: none !important;
}
/* Also hide the tab border element Streamlit injects */
div[data-baseweb="tab-border"] {
    background-color: transparent !important;
    display: none !important;
}
button[data-baseweb="tab"] {
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
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
::-webkit-scrollbar       { width:6px; height:6px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }
::-webkit-scrollbar-thumb:hover { background:var(--accent); }

/* ══ HIDE STREAMLIT CHROME ══════════════════════════════════ */
[data-testid="stToolbar"]    { display:none !important; }
[data-testid="stDecoration"] { display:none !important; }
#MainMenu                    { display:none !important; }
footer                       { display:none !important; }
/* ══ SIDEBAR CONTROL BUTTON ══════════════════════════════════ */
header[data-testid="stHeader"] { display: none !important; }

section[data-testid="stSidebar"] { z-index: 100000 !important; }

[data-testid="stSidebarCollapsedControl"] button,
button[data-testid="stSidebarCollapseButton"],
button[aria-label="Open sidebar"],
button[aria-label="Close sidebar"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background-color: var(--accent) !important;
    color: #000 !important;
    border: 2px solid #000 !important;
    border-radius: 6px !important;
    width: 46px !important;
    height: 46px !important;
    position: fixed !important;
    top: 20px !important;
    left: 20px !important;
    z-index: 2147483647 !important;
    box-shadow: 0 0 20px rgba(0, 229, 160, 0.6) !important;
    transition: all 0.3s ease !important;
}

[data-testid="stSidebarCollapsedControl"] svg,
button[aria-label="Open sidebar"] svg,
button[aria-label="Close sidebar"] svg {
    fill: #000 !important;
    width: 28px !important;
    height: 28px !important;
}

[data-testid="stSidebarCollapsedControl"] button:hover {
    transform: scale(1.1) !important;
    background-color: #fff !important;
    box-shadow: 0 0 30px var(--accent) !important;
}

.stApp::before { z-index: 9999 !important; pointer-events: none !important; }


/* ══ PROGRESS BAR ═══════════════════════════════════════════ */
.stProgress > div > div > div { background:var(--accent) !important; }

/* ══ COMPARE CARD ═══════════════════════════════════════════ */
.compare-card {
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:6px;
    padding:1.2rem 1.4rem;
    position:relative;
    overflow:hidden;
}
.compare-card::before {
    content:'';
    position:absolute;
    top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg,var(--danger),var(--accent));
}

/* ════════════════════════════════════════════════════════════
   REUSABLE LAYOUT CLASSES  (used in inline HTML throughout)
   ════════════════════════════════════════════════════════════ */

/* Section headers (tab titles) */
.tab-title {
    font-family:'Syne',sans-serif;
    font-size:clamp(1.3rem, 4vw, 1.8rem);
    font-weight:800;
    color:#dce8f0;
    letter-spacing:-0.02em;
    margin-bottom:0.2rem;
}
.tab-title-bar {
    width:60px; height:2px;
    background:#00e5a0;
    margin-bottom:0.6rem;
}

/* ── Banner cards (info/warning/success panels) ────────────── */
.banner {
    border-radius:6px;
    padding:1.3rem 1.5rem;
    margin-bottom:1rem;
}
.banner-warn  { background:#1a1008; border:1px solid #ffb34755; border-left:4px solid #ffb347; }
.banner-ok    { background:#061a10; border:1px solid #00e5a033; border-left:4px solid #00e5a0; }
.banner-info  { background:#0a1820; border:1px solid #1c3a5055; border-left:4px solid #7eb8f7; }
.banner-title {
    font-family:'Syne',sans-serif;
    font-size:clamp(0.85rem, 2.5vw, 1rem);
    font-weight:800;
    margin-bottom:0.35rem;
}
.banner-body  {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.68rem, 2vw, 0.75rem);
    line-height:1.7;
}

/* ── Column info card (per-column panels in Smart Clean) ───── */
.col-card {
    background:#0c1014;
    border:1px solid #1c2a35;
    border-radius:6px;
    padding:1.2rem 1.4rem;
    margin-bottom:0.9rem;
    box-sizing:border-box;
}
.col-card-header {
    display:flex;
    align-items:center;
    flex-wrap:wrap;
    gap:0.5rem;
    margin-bottom:0.8rem;
}
.col-card-name {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.78rem, 2.5vw, 0.88rem);
    font-weight:600;
    color:#dce8f0;
}
.col-card-badge {
    border-radius:3px;
    padding:1px 7px;
    font-family:'JetBrains Mono',monospace;
    font-size:0.62rem;
    white-space:nowrap;
}
.badge-num   { background:#0a1f30; border:1px solid #1c4060; color:#7eb8f7; }
.badge-text  { background:#101820; border:1px solid #2a3a40; color:#4a8090; }
.col-card-meta {
    font-family:'JetBrains Mono',monospace;
    font-size:0.68rem;
    color:#4a6070;
}

/* ── Stats row (mean / median / mode) ──────────────────────── */
.stats-row {
    display:flex;
    flex-wrap:wrap;
    gap:1.2rem;
    margin-bottom:0.8rem;
}
.stat-item {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.68rem, 2vw, 0.75rem);
    color:#4a7060;
    white-space:nowrap;
}
.stat-val { color:#dce8f0; font-weight:600; }

/* ── Recommendation line ────────────────────────────────────── */
.rec-line {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.65rem, 1.8vw, 0.7rem);
    color:#2a7050;
}

/* ── Junk-word chip row ─────────────────────────────────────── */
.junk-chip-row {
    display:flex;
    flex-wrap:wrap;
    gap:6px;
    margin-bottom:0.8rem;
}
.junk-chip {
    background:#0a1820;
    border:1px solid #1c3a50;
    border-radius:3px;
    padding:2px 9px;
    font-family:'JetBrains Mono',monospace;
    font-size:0.68rem;
    color:#7eb8f7;
}

/* ── Cleaning result banner ─────────────────────────────────── */
.clean-banner {
    background:linear-gradient(135deg,#061a10,#0a2018);
    border:1px solid #00e5a055;
    border-radius:8px;
    padding:1.2rem 1.5rem;
    margin-bottom:1.5rem;
    display:flex;
    align-items:center;
    flex-wrap:wrap;
    gap:1rem;
}
.clean-banner-icon  { font-size:clamp(1.5rem, 5vw, 2rem); flex-shrink:0; }
.clean-banner-text  { flex:1; min-width:160px; }
.clean-banner-title {
    font-family:'Syne',sans-serif;
    font-size:clamp(0.95rem, 3vw, 1.1rem);
    font-weight:800;
    color:#00e5a0;
}
.clean-banner-sub {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.68rem, 2vw, 0.76rem);
    color:#5a8060;
    margin-top:0.2rem;
}
.clean-banner-grade {
    text-align:center;
    flex-shrink:0;
}
.clean-banner-grade-val {
    font-family:'Syne',sans-serif;
    font-size:clamp(1.5rem, 5vw, 2rem);
    font-weight:800;
    line-height:1;
}
.clean-banner-grade-lbl {
    font-family:'JetBrains Mono',monospace;
    font-size:0.62rem;
    color:#4a6070;
}

/* ── Result cards grid (4-up → 2-up → 1-up) ────────────────── */
.result-cards {
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:0.75rem;
    margin-bottom:1.5rem;
}
.result-card {
    border-radius:8px;
    padding:1rem 1.1rem;
    box-sizing:border-box;
}
.result-card-icon   { font-size:1.3rem; margin-bottom:0.6rem; }
.result-card-number {
    font-family:'Syne',sans-serif;
    font-size:clamp(1.3rem, 4vw, 1.7rem);
    font-weight:800;
    line-height:1;
    margin-bottom:0.6rem;
}
.result-card-title {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.68rem, 2vw, 0.76rem);
    color:#dce8f0;
    font-weight:600;
    margin-bottom:0.6rem;
}
.result-card-desc {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.62rem, 1.8vw, 0.68rem);
    color:#4a6070;
    line-height:1.5;
}

/* ── Before/After table ─────────────────────────────────────── */
.ba-table { background:#0c1014; border:1px solid #1c2a35; border-radius:6px; padding:0.7rem 1.1rem; }
.ba-header {
    display:flex;
    padding:0.4rem 0;
    border-bottom:2px solid #1c2a35;
    font-family:'JetBrains Mono',monospace;
    font-size:0.62rem;
    letter-spacing:0.12em;
    text-transform:uppercase;
    color:#4a6070;
}
.ba-row {
    display:flex;
    align-items:center;
    padding:0.5rem 0;
    border-bottom:1px solid #1c2a35;
    font-family:'JetBrains Mono',monospace;
}
.ba-label { flex:2; font-size:0.73rem; color:#6a8090; }
.ba-before { flex:1; font-size:0.88rem; font-weight:600; color:#ff6060; text-align:right; }
.ba-arrow  { flex:0 0 2rem; font-size:0.88rem; color:#4a6070; text-align:center; }
.ba-after  { flex:1; font-size:0.88rem; font-weight:600; }

/* ── Approval summary panel ─────────────────────────────────── */
.ops-panel {
    background:#0c1014;
    border:1px solid #00e5a033;
    border-radius:6px;
    padding:1.3rem 1.5rem;
    margin-bottom:1rem;
}
.ops-title {
    font-family:'JetBrains Mono',monospace;
    font-size:0.72rem;
    color:#00e5a0;
    letter-spacing:0.1em;
    margin-bottom:0.6rem;
}
.ops-line {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.66rem, 2vw, 0.73rem);
    color:#dce8f0;
    padding:3px 0;
    border-bottom:1px solid #1c2a35;
}
.ops-footer {
    font-family:'JetBrains Mono',monospace;
    font-size:0.65rem;
    color:#4a6070;
    margin-top:0.6rem;
}

/* ── Insight cards (Executive Summary) ──────────────────────── */
.insight-card {
    border-radius:6px;
    padding:1.3rem 1.4rem;
    margin-bottom:0.7rem;
    position:relative;
    border:1px solid;
}
.insight-header {
    display:flex;
    align-items:flex-start;
    gap:0.7rem;
    flex-wrap:wrap;
}
.insight-icon   { font-size:1.1rem; flex-shrink:0; }
.insight-title  {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.76rem, 2.2vw, 0.85rem);
    font-weight:600;
    color:#dce8f0;
    flex:1;
    min-width:120px;
}
.insight-badge  { margin-left:auto; flex-shrink:0; }
.insight-body   {
    font-family:'JetBrains Mono',monospace;
    font-size:clamp(0.66rem, 1.9vw, 0.73rem);
    color:#6a8090;
    margin-top:0.4rem;
    line-height:1.6;
}
.insight-impact {
    font-family:'JetBrains Mono',monospace;
    font-size:0.65rem;
    margin-top:0.3rem;
    opacity:0.7;
}

/* ════════════════════════════════════════════════════════════
   RESPONSIVE BREAKPOINTS
   ════════════════════════════════════════════════════════════ */

/* ── Tablet ≤ 1024px ──────────────────────────────────────── */
@media (max-width:1024px) {
    .main .block-container { padding-left:1.2rem !important; padding-right:1.2rem !important; max-width:100% !important; }
    .result-cards          { grid-template-columns:repeat(2,1fr) !important; }
}

/* ── Mobile ≤ 768px ───────────────────────────────────────── */
@media (max-width:768px) {

    /* Layout */
    .main .block-container {
        padding:0.8rem 0.6rem 2rem !important;
        max-width:100% !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        min-width:82vw !important;
        width:82vw !important;
    }

    /* Tabs — horizontal scroll, no wrap */
    div[data-testid="stTabs"] > div:first-child {
        overflow-x:auto !important;
        flex-wrap:nowrap !important;
        -webkit-overflow-scrolling:touch !important;
        scrollbar-width:none !important;
    }
    div[data-testid="stTabs"] > div:first-child::-webkit-scrollbar { display:none !important; }
    button[data-baseweb="tab"] {
        font-size:0.6rem !important;
        padding:0.55rem 0.65rem !important;
        white-space:nowrap !important;
        flex-shrink:0 !important;
    }

    /* Metric cards */
    div[data-testid="metric-container"] { padding:1.1rem 1.2rem !important; }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size:1.4rem !important; }
    div[data-testid="metric-container"] label { font-size:0.58rem !important; }

    /* Buttons */
    .stButton > button {
        width:100% !important;
        font-size:0.74rem !important;
        padding:0.65rem 1rem !important;
        min-height:44px !important;
    }
    .stDownloadButton > button { width:100% !important; min-height:44px !important; }

    /* Inputs */
    .stTextInput input        { font-size:0.82rem !important; min-height:42px !important; }
    div[data-baseweb="select"] > div { font-size:0.78rem !important; min-height:42px !important; }
    .stSlider [data-baseweb="slider"] div[role="slider"] { width:22px !important; height:22px !important; }

    /* Radio / Checkbox */
    .stRadio > div          { flex-direction:column !important; }
    .stRadio label, .stCheckbox label {
        font-size:0.75rem !important;
        min-height:40px !important;
        display:flex !important;
        align-items:center !important;
    }

    /* Expanders */
    details summary {
        font-size:0.76rem !important;
        padding:0.65rem 0.8rem !important;
        min-height:44px !important;
        display:flex !important;
        align-items:center !important;
    }

    /* Dataframes */
    .stDataFrame                { overflow-x:auto !important; -webkit-overflow-scrolling:touch !important; }
    .stDataFrame th, .stDataFrame td { font-size:0.68rem !important; white-space:nowrap !important; }

    /* Plotly */
    .js-plotly-plot, .plotly   { max-width:100% !important; overflow:hidden !important; }

    /* Our layout classes */
    .result-cards              { grid-template-columns:repeat(2,1fr) !important; }
    .stats-row                 { gap:0.8rem !important; }
    .clean-banner              { padding:0.9rem 1rem !important; }
    .col-card                  { padding:1.1rem 1.2rem !important; }
    .ba-header, .ba-row        { font-size:0.68rem !important; }

    /* Inner dashboard tabs */
    div[data-testid="stTabs"] div[data-testid="stTabs"] button[data-baseweb="tab"] {
        font-size:0.55rem !important;
        padding:0.4rem 0.45rem !important;
    }
}

/* ── Small phones ≤ 480px ────────────────────────────────── */
@media (max-width:480px) {

    .main .block-container { padding:0.6rem 0.4rem 1.5rem !important; }

    button[data-baseweb="tab"] { font-size:0.55rem !important; padding:0.45rem 0.5rem !important; }

    div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size:1.1rem !important; }

    /* All 4 cards stack to 1 column */
    .result-cards { grid-template-columns:1fr !important; }

    /* Stacked columns */
    div[data-testid="column"] { min-width:100% !important; }

    /* Before/after rows stack */
    .ba-row   { flex-wrap:wrap; gap:0.2rem; padding:0.6rem 0; }
    .ba-label { flex:0 0 100% !important; }
    .ba-arrow { flex:0 0 1.5rem !important; }

    /* Clean banner — stack grade below */
    .clean-banner       { flex-direction:column; align-items:flex-start; }
    .clean-banner-grade { width:100%; border-top:1px solid #1c2a35; padding-top:0.6rem; margin-top:0.3rem; text-align:left; }

    .hero-title { font-size:2rem !important; }
    .hero-sub   { font-size:0.72rem !important; }
}

/* ── Touch devices — 44px targets everywhere ──────────────── */
@media (hover:none) and (pointer:coarse) {
    button:not([data-testid="stSidebarCollapseButton"]):not([aria-label="Open sidebar"]):not([aria-label="Close sidebar"]),
    [role="button"], .stCheckbox label, .stRadio label { min-height:44px !important; }
    .stButton > button:hover, section[data-testid="stSidebar"] .stButton > button:hover {
        transform:none !important;
    }
}

/* ══ ANIMATIONS ═══════════════════════════════════════════════ */
@keyframes fadeInUp {
    from { opacity:0; transform:translateY(14px); }
    to   { opacity:1; transform:translateY(0);    }
}
@keyframes fadeIn {
    from { opacity:0; }
    to   { opacity:1; }
}
@keyframes slideInLeft {
    from { opacity:0; transform:translateX(-16px); }
    to   { opacity:1; transform:translateX(0);     }
}
@keyframes glowPulse {
    0%,100% { box-shadow:0 0 6px rgba(0,229,160,0.15); }
    50%     { box-shadow:0 0 24px rgba(0,229,160,0.45); }
}
@keyframes countUp {
    from { opacity:0; transform:scale(0.88); }
    to   { opacity:1; transform:scale(1);    }
}
.anim-up    { animation:fadeInUp    0.32s ease both; }
.anim-in    { animation:fadeIn      0.38s ease both; }
.anim-left  { animation:slideInLeft 0.32s ease both; }
.anim-glow  { animation:glowPulse   2.6s  ease-in-out infinite; }
.anim-count { animation:countUp     0.4s  ease both; }
.anim-up:nth-child(1){ animation-delay:0s;    }
.anim-up:nth-child(2){ animation-delay:0.06s; }
.anim-up:nth-child(3){ animation-delay:0.12s; }
.anim-up:nth-child(4){ animation-delay:0.18s; }

/* ══ CARD TITLE FONT — NUCLEAR FIX ═══════════════════════════ */
/* bleach strips !important from inline styles, so inline       */
/* style='font-family:Syne' loses to body's !important rule.    */
/* Classes defined here in <style> are never touched by bleach. */
.card-title,
div[data-testid="stMarkdownContainer"] .card-title {
    font-family: Syne, 'Syne', sans-serif !important;
    font-style:  normal   !important;
    font-weight: 800      !important;
    text-decoration: none !important;
    color: #dce8f0        !important;
    letter-spacing: -0.01em !important;
}
div[data-testid="stMarkdownContainer"] [style*="font-weight:800"],
div[data-testid="stMarkdownContainer"] [style*="font-weight: 800"] {
    font-family: Syne, 'Syne', sans-serif !important;
    font-style: normal !important;
}
div[data-testid="stMarkdownContainer"] [style*="Syne"] {
    font-family: Syne, 'Syne', sans-serif !important;
    font-style: normal !important;
}

/* ══ DASHBOARD KPI ════════════════════════════════════════════ */
.dash-kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 2px solid var(--accent);
    border-radius: 6px;
    padding: 1rem 1.2rem;
    animation: fadeInUp 0.32s ease both;
}

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
        # ── file info card ────────────────────────
        fsize_kb = len(uploaded_file.getvalue()) / 1024
        fsize_str = f"{fsize_kb:.1f} KB" if fsize_kb < 1024 else f"{fsize_kb/1024:.1f} MB"
        st.markdown(f"""
        <div style='
            background:#0a1a12;
            border:1px solid #1c3825;
            border-left:3px solid #00e5a0;
            border-radius:3px;
            padding:1.1rem 1.2rem;
            margin-bottom:0.8rem;
        '>
            <div style='font-size:0.65rem;color:#4a6070;letter-spacing:0.12em;
                        text-transform:uppercase;margin-bottom:0.6rem;'>File loaded</div>
            <div style='font-size:0.8rem;color:#dce8f0;font-weight:600;
                        word-break:break-all;'>{uploaded_file.name}</div>
            <div style='font-size:0.68rem;color:#4a6070;margin-top:0.2rem;'>{fsize_str}</div>
        </div>
        """, unsafe_allow_html=True)

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

        # ── AI Consultant section ─────────────────────────────
        st.markdown(
            "<div style='font-family:\"Syne\",sans-serif;font-size:0.8rem;font-weight:800;"
            "color:#00e5a0;letter-spacing:0.05em;margin-bottom:0.6rem;'>🤖 AI CONSULTANT</div>",
            unsafe_allow_html=True
        )
        gemini_api_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Free key from aistudio.google.com — 1,500 requests/day, no credit card needed.",
            key="gemini_api_key",
        )
        if gemini_api_key:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;"
                "color:#00e5a0;margin-top:-0.3rem;'>✓ Key loaded</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;"
                "color:#2a4a38;margin-top:-0.3rem;'>Free key → aistudio.google.com</div>",
                unsafe_allow_html=True
            )
        st.markdown("---")
        st.markdown(
            "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;"
            "color:#2a4a38;letter-spacing:0.1em;'>BUILT ON DATAAUDITOR v4 + GEMINI</div>",
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════
# MAIN — guard: nothing uploaded yet
# ══════════════════════════════════════════════════════════════



if not uploaded_file:
    # ── animated accent line ──────────────────────────────────
    st.markdown("""
    <style>
    @keyframes scanline {
        0%   { transform: translateX(-100%); }
        100% { transform: translateX(400%); }
    }
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(20px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .hero-title    { animation: fadeUp 0.6s ease both; }
    .hero-sub      { animation: fadeUp 0.6s ease 0.15s both; }
    .hero-steps    { animation: fadeUp 0.6s ease 0.3s both; }
    .scan-bar {
        position: relative;
        height: 2px;
        background: var(--border);
        overflow: hidden;
        margin: 2rem 0 2.5rem 0;
    }
    .scan-bar::after {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 30%;
        height: 100%;
        background: linear-gradient(90deg, transparent, #00e5a0, transparent);
        animation: scanline 2.5s ease-in-out infinite;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        "<div class='hero-title' style='"
        "font-family:\"Syne\",sans-serif;"
        "font-size:clamp(2rem, 5vw, 4rem);"
        "font-weight:800;"
        "color:#dce8f0;"
        "letter-spacing:-0.03em;"
        "line-height:1;"
        "margin-bottom:0.7rem;'>"
        "DATA<br>"
        "<span style='color:#00e5a0;'>INTELLIGENCE</span><br>"
        "<span style='font-size:0.45em;color:#4a6070;font-weight:400;"
        "letter-spacing:0.05em;'>AUDIT ENGINE</span>"
        "</div>",
        unsafe_allow_html=True
    )

    st.markdown("<div class='scan-bar'></div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='hero-sub' style='"
        "font-family:\"JetBrains Mono\",monospace;"
        "font-size:0.85rem;"
        "color:#4a6070;"
        "letter-spacing:0.05em;"
        "max-width:560px;"
        "line-height:1.7;"
        "margin-bottom:2.5rem;'>"
        "Upload any CSV, Excel, JSON or Parquet file. "
        "The engine runs <span style='color:#dce8f0;'>17 quality checks</span>, "
        "shows you exactly what's wrong, and lets you decide what gets fixed — "
        "<span style='color:#00e5a0;'>nothing changes without your approval.</span>"
        "</div>",
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    for col, num, label, desc, icon in [
        (c1, "01", "Audit",   "17 silent checks · zero modifications",          "🔬"),
        (c2, "02", "Approve", "You decide what gets fixed, check by check",       "✅"),
        (c3, "03", "Clean",   "Only the fixes you approved are applied",           "🧹"),
        (c4, "04", "Export",  "CSV · Excel · SQL Schema ready to deploy",          "📦"),
    ]:
        col.markdown(f"""
        <div class='hero-steps' style='
            background:#0c1014;
            border:1px solid #1c2a35;
            border-top:2px solid #00e5a0;
            padding:1.4rem 1.2rem 1.6rem;
            position:relative;
            transition: border-color 0.2s;
        '>
            <div style='
                position:absolute;top:1rem;right:1rem;
                font-size:1.2rem;opacity:0.4;
            '>{icon}</div>
            <div style='
                font-family:"Syne",sans-serif;
                font-size:2.4rem;
                font-weight:800;
                color:#1c2a35;
                line-height:1;
                margin-bottom:0.8rem;
                user-select:none;
            '>{num}</div>
            <div style='
                font-family:"JetBrains Mono",monospace;
                font-size:0.78rem;
                font-weight:600;
                color:#00e5a0;
                letter-spacing:0.14em;
                text-transform:uppercase;
                margin-bottom:0.8rem;
            '>{label}</div>
            <div style='
                font-family:"JetBrains Mono",monospace;
                font-size:0.68rem;
                color:#4a6070;
                line-height:1.6;
            '>{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── supported formats row ─────────────────────────────────
    st.markdown(
            "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.68rem;"
            "color:#2a4040;letter-spacing:0.15em;text-transform:uppercase;'>"
            "← Upload a file in the sidebar to begin &nbsp;·&nbsp; "
            "Supports: CSV &nbsp;·&nbsp; XLSX &nbsp;·&nbsp; JSON &nbsp;·&nbsp; PARQUET"
            "</div>",
            unsafe_allow_html=True
        )
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

# Save to a temp file so DataAuditor (which needs a path) can load it.
# We track the path in session_state so we can clean it up after the audit.
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
    st.session_state.ai_strategy   = None   # AI Consultant result

# Reset if a new file was uploaded
if st.session_state.file_name != uploaded_file.name:
    st.session_state.audit_report  = None
    st.session_state.clean_df      = None
    st.session_state.audit_log     = []
    st.session_state.clean_summary = None
    st.session_state.file_name     = uploaded_file.name
    st.session_state.ai_strategy   = None   # clear AI strategy on new file

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
        finally:
            # FIX: always delete the temp file after the audit — whether it
            # succeeded or failed — to prevent one orphaned file per rerun.
            try:
                os.unlink(_tmp_path)
            except OSError:
                pass

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
        f"Based on live audit data"
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
            border-radius:6px;
            padding:1.2rem 1.4rem;
            margin-bottom:0.6rem;
        '>
            <div style='display:flex;align-items:center;gap:0.6rem;margin-bottom:0.6rem;'>
                <span style='font-size:1.1rem;'>{ins['icon']}</span>
                <span style='
                    font-family:"Syne",sans-serif;
                    font-size:1rem;
                    font-weight:800;
                    font-style:normal;
                    line-height:1.5;
                    color:#dce8f0;
                    text-decoration:none !important;
                '>{ins['title'].replace(chr(32), chr(160))}</span>
                <span style='
                    margin-left:auto;
                    font-family:"JetBrains Mono",monospace;
                    font-size:0.6rem;
                    letter-spacing:0.08em;
                    color:{sev_c};
                    border:1px solid {sev_c}66;
                    padding:2px 10px;
                    border-radius:3px;
                    white-space:nowrap;
                    flex-shrink:0;
                '>{ins['severity']}</span>
            </div>
            <div style='font-family:"JetBrains Mono",monospace;font-size:0.73rem;color:#8a9aaa;line-height:1.7;margin-bottom:0.5rem;'>{ins['body']}</div>
            <div style='font-family:"JetBrains Mono",monospace;font-size:0.67rem;color:#4a6070;line-height:1.5;'>↳ {ins['impact']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    g_col, _ = st.columns([1, 3])

    with g_col:
        score = report["health_score"]
        grade = report["health_grade"]
        st.plotly_chart(make_gauge(score), use_container_width=True)
        st.markdown(
            f"<div style='text-align:center;font-family:\"Syne\",sans-serif;"
            f"font-size:1.4rem;font-weight:800;letter-spacing:0.05em;color:{_score_color(score)};'>Grade {grade}</div>",
            unsafe_allow_html=True
        )

    # ── Data Preview ─────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<span style='font-family:\"JetBrains Mono\",monospace;font-size:.7rem;"
        "color:#00e5a0;letter-spacing:.15em;text-transform:uppercase;'>◈ Data Preview</span>",
        unsafe_allow_html=True
    )
    prev_rows = st.slider("Rows to preview", 5, min(100, len(df_raw)), 10, key="preview_rows")
    st.dataframe(df_raw.head(prev_rows), use_container_width=True)
    st.markdown(
        f"<small style='color:#4a6070;'>"
        f"Showing {prev_rows} of {len(df_raw):,} rows · "
        f"{len(df_raw.columns)} columns · "
        f"{df_raw.isnull().sum().sum():,} total nulls</small>",
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
        f"<small style='color:#4a6070;font-family:\"JetBrains Mono\",monospace;font-size:0.68rem;'>Scanned at {report['scanned_at']} &nbsp;·&nbsp; "
        f"File: <code style='color:#00e5a0;'>{report['file']}</code></small>",
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
# TAB 3 — SMART CLEAN  (Redesigned)
# ─────────────────────────────────────────────

# ── Junk words: values written in cells that mean "no data" ───
JUNK_WORDS = {
    "unknown", "unknwon", "unknow",
    "error", "err", "#error", "#err",
    "n/a", "na", "n.a", "n.a.", "#n/a", "#na",
    "null", "none", "nil",
    "missing", "miss",
    "undefined", "undef",
    "-", "--", "---", "?", "??",
    "not available", "not applicable",
    "empty", "blank",
    "tbd", "tbc", "todo",
}

@st.cache_data(show_spinner=False)
def _scan_junk(df_bytes, file_name):
    """
    Scan only text (object) columns for junk words. Returns {col: {word: count}}.

    We accept df_bytes + file_name (instead of a DataFrame directly) so that
    Streamlit's @st.cache_data can hash the arguments and cache correctly.
    The bytes are decoded into a DataFrame here; load_raw() handles the same
    bytes separately and its result is cached independently — both use
    @st.cache_data so the actual I/O only happens once per unique file.
    """
    import io as _io, pandas as _pd
    ext = file_name.rsplit(".", 1)[-1].lower()
    buf = _io.BytesIO(df_bytes)
    loaders = {
        "csv":     lambda: _pd.read_csv(buf),
        "xlsx":    lambda: _pd.read_excel(buf),
        "xls":     lambda: _pd.read_excel(buf),
        "json":    lambda: _pd.read_json(buf),
        "parquet": lambda: _pd.read_parquet(buf),
    }
    df = loaders[ext]()
    result = {}
    for col in df.select_dtypes(include="object").columns:
        normed = df[col].dropna().astype(str).str.strip().str.lower()
        hits = {w: int((normed == w).sum()) for w in JUNK_WORDS if (normed == w).any()}
        if hits:
            result[col] = hits
    return result

junk_map = _scan_junk(raw_bytes, uploaded_file.name)

def _real_type(series):
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    real = series.dropna().astype(str).str.strip()
    real = real[~real.str.lower().isin(JUNK_WORDS)]
    if len(real) == 0:
        return "text"
    converted = pd.to_numeric(real, errors="coerce")
    if converted.notna().sum() / len(real) >= 0.7:
        return "numeric"
    return "text"

if "null_fill_strategy" not in st.session_state:
    st.session_state.null_fill_strategy = {}
if "junk_approve" not in st.session_state:
    st.session_state.junk_approve = {}
if "fe_approved" not in st.session_state:
    st.session_state.fe_approved = {}   # {feature_name: bool}

with tab3:
    st.markdown(
        "<div style='font-family:\"Syne\",sans-serif;font-size:1.8rem;font-weight:800;"
        "color:#dce8f0;letter-spacing:-0.02em;margin-bottom:0.2rem;'>Smart Clean</div>"
        "<div style='width:60px;height:2px;background:#00e5a0;margin-bottom:0.6rem;'></div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<small style='color:#4a6070;'>Review every issue and choose your options. "
        "Nothing changes until you click <b>Apply Selected Fixes</b> in the Review tab.</small>",
        unsafe_allow_html=True
    )

    # ══════════════════════════════════════════════════════════
    # SUB-TABS
    # ══════════════════════════════════════════════════════════
    sc_tab1, sc_tab2, sc_tab3, sc_tab4 = st.tabs([
        "🤖  AI Advisor",
        "🧹  Junk Values & Nulls",
        "🔧  Data Fixes",
        "▶️  Review & Apply",
    ])

    # ──────────────────────────────────────────────────────────
    # Shared state: build permissions dict that all sub-tabs write to
    # ──────────────────────────────────────────────────────────
    null_check   = checks.get("nulls", {})
    null_by_col  = null_check.get("by_column", {})

    high_checks   = {k: v for k, v in checks.items()
                     if k != "nulls" and v.get("fix_key") and v.get("severity") == "HIGH"   and v.get("found")}
    medium_checks = {k: v for k, v in checks.items()
                     if k != "nulls" and v.get("fix_key") and v.get("severity") == "MEDIUM" and v.get("found")}
    ok_checks     = {k: v for k, v in checks.items()
                     if k != "nulls" and v.get("fix_key") and v.get("severity") == "OK"}

    _api_key     = st.session_state.get("gemini_api_key", "").strip()
    _ai          = st.session_state.get("ai_strategy")
    _ai_perms    = _ai.get("permissions", {}) if (_ai and not _ai.get("error")) else {}

    # ══════════════════════════════════════════════════════════
    # SUB-TAB 1 — AI ADVISOR
    # ══════════════════════════════════════════════════════════
    with sc_tab1:

        # ── Header panel ──────────────────────────────────────
        st.markdown("""
        <div style='background:linear-gradient(135deg,#060f14,#091820);
            border:1px solid #00e5a033;border-radius:6px;
            padding:1.2rem 1.5rem;margin-bottom:1.2rem;'>
            <div style='display:flex;align-items:center;gap:0.8rem;margin-bottom:0.8rem;'>
                <span style='font-size:1.6rem;'>🤖</span>
                <div>
                    <div style='font-family:"Syne",sans-serif;font-size:1.1rem;font-weight:800;
                        color:#dce8f0;'>AI Advisor</div>
                    <div style='font-family:"JetBrains Mono",monospace;font-size:0.62rem;
                        color:#4a6070;letter-spacing:0.1em;'>POWERED BY GEMINI</div>
                </div>
            </div>
            <div style='font-family:"JetBrains Mono",monospace;font-size:0.73rem;
                color:#4a6070;line-height:1.7;'>
                Click <b style='color:#dce8f0;'>Generate AI Strategy</b> to have the AI review your audit report.
                It recommends which fixes to apply, explains its reasoning, and suggests new columns you can derive
                from your existing data. Every suggestion appears as a card — approve or skip each one individually.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Generate button ────────────────────────────────────
        ai_gen_col, ai_status_col = st.columns([2, 5])
        with ai_gen_col:
            ai_btn = st.button(
                "🪄  Generate AI Strategy",
                use_container_width=True,
                disabled=(not _api_key or st.session_state.audit_report is None),
                key="ai_generate_btn",
            )
        with ai_status_col:
            if not _api_key:
                st.markdown(
                    "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.7rem;"
                    "color:#2a4a38;padding-top:10px;'>← Enter Gemini API key in the sidebar to enable</div>",
                    unsafe_allow_html=True
                )
            elif _ai and not _ai.get("error"):
                _conf_now = _ai.get("confidence", "")
                _conf_col = {"HIGH": "#00e5a0", "MEDIUM": "#ffb347", "LOW": "#ff4444"}.get(_conf_now, "#4a6070")
                st.markdown(
                    f"<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.7rem;"
                    f"color:#4a6070;padding-top:10px;'>✓ Strategy loaded — "
                    f"<span style='color:{_conf_col};font-weight:600;'>Confidence: {_conf_now}</span>"
                    f" &nbsp;·&nbsp; click again to refresh</div>",
                    unsafe_allow_html=True
                )

        # ── Run the API call ───────────────────────────────────
        if ai_btn and _api_key:
            with st.spinner("🧠  AI is reading your audit report…"):
                try:
                    from ai_consultant import get_ai_strategy  # type: ignore
                    _strategy = get_ai_strategy(st.session_state.audit_report, _api_key)
                    st.session_state.ai_strategy = _strategy
                    st.rerun()
                except ImportError:
                    st.error("ai_consultant.py not found — place it in the same directory as app.py.")

        # ── Display results ────────────────────────────────────
        _ai = st.session_state.get("ai_strategy")

        if _ai and _ai.get("error"):
            st.markdown(
                f"<div style='background:#1a0808;border:1px solid #ff444455;"
                f"border-left:3px solid #ff4444;border-radius:6px;"
                f"padding:1.2rem 1.4rem;margin-top:0.8rem;"
                f"font-family:\"JetBrains Mono\",monospace;font-size:0.75rem;color:#ff6060;'>"
                f"⚠ {_ai['error']}</div>",
                unsafe_allow_html=True
            )

        elif _ai and not _ai.get("error"):
            _ai_perms   = _ai.get("permissions", {})
            _rationale  = _ai.get("rationale", {})
            _conf       = _ai.get("confidence", "MEDIUM")
            _conf_c     = {"HIGH": "#00e5a0", "MEDIUM": "#ffb347", "LOW": "#ff4444"}.get(_conf, "#4a6070")
            _conf_bg    = {"HIGH": "#061a10", "MEDIUM": "#1a1008", "LOW": "#1a0808"}.get(_conf, "#0c1014")

            # ── Executive summary card — shown above both tabs ─
            if _ai.get("executive_summary"):
                st.markdown(f"""
                <div style='background:{_conf_bg};border:1px solid {_conf_c}33;
                    border-left:4px solid {_conf_c};border-radius:6px;
                    padding:1.3rem 1.5rem;margin:1rem 0 0.8rem;'>
                    <div style='display:flex;align-items:center;gap:0.6rem;margin-bottom:0.6rem;'>
                        <span style='font-family:"Syne",sans-serif;font-size:0.95rem;
                            font-weight:800;color:#dce8f0 !important;text-decoration:none !important;'>📋 AI Assessment</span>
                        <span style='margin-left:auto;font-family:"JetBrains Mono",monospace;
                            font-size:0.62rem;color:{_conf_c};border:1px solid {_conf_c}55;
                            padding:2px 10px;border-radius:20px;letter-spacing:0.08em;'>
                            CONFIDENCE: {_conf}</span>
                    </div>
                    <div style='font-family:"JetBrains Mono",monospace;font-size:0.76rem;
                        color:#c0d0d8;line-height:1.8;'>{_ai["executive_summary"]}</div>
                </div>
                """, unsafe_allow_html=True)

            # ── Risk flags — shown above both tabs ─────────────
            if _ai.get("risk_flags"):
                flags_html = "".join(
                    f"<div style='display:flex;align-items:flex-start;gap:0.5rem;padding:5px 0;"
                    f"border-bottom:1px solid #2a1a00;'>"
                    f"<span style='color:#ffb347;flex-shrink:0;'>⚑</span>"
                    f"<span style='font-family:\"JetBrains Mono\",monospace;font-size:0.72rem;"
                    f"color:#c09060;'>{flag}</span></div>"
                    for flag in _ai["risk_flags"]
                )
                st.markdown(f"""
                <div style='background:#1a1008;border:1px solid #ffb34733;
                    border-radius:6px;padding:1.2rem 1.4rem;margin-bottom:0.8rem;'>
                    <div style='font-family:"JetBrains Mono",monospace;font-size:0.65rem;
                        color:#ffb347;letter-spacing:0.12em;margin-bottom:0.8rem;'>⚠ RISK FLAGS</div>
                    {flags_html}
                </div>
                """, unsafe_allow_html=True)

            # ══════════════════════════════════════════════════
            # AI ADVISOR INNER TABS
            # ══════════════════════════════════════════════════
            ai_inner_tab1, ai_inner_tab2 = st.tabs([
                "🧹  Cleaning Suggestions",
                "✨  Feature Engineering",
            ])

            # ── INNER TAB 1 — CLEANING SUGGESTIONS ────────────
            with ai_inner_tab1:

                if not _ai_perms:
                    st.markdown("""
                    <div style='text-align:center;padding:2.5rem 1rem;'>
                        <div style='font-size:2rem;margin-bottom:0.8rem;'>✅</div>
                        <div style='font-family:"Syne",sans-serif;font-size:0.95rem;font-weight:800;
                            color:#00e5a0;margin-bottom:0.4rem;'>No cleaning operations suggested</div>
                        <div style='font-family:"JetBrains Mono",monospace;font-size:0.7rem;color:#4a6070;'>
                            The AI found no issues that require fixing in your dataset.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # ── Sort by severity then by AI recommendation ─────
                    _SEV_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "OK": 3}
                    _SEV_META  = {
                        "HIGH":   {"c": "#ff4444", "bg": "#160606"},
                        "MEDIUM": {"c": "#ffb347", "bg": "#141008"},
                        "LOW":    {"c": "#7eb8f7", "bg": "#0a1420"},
                        "OK":     {"c": "#00e5a0", "bg": "#06120a"},
                    }

                    _enriched = []
                    for chk_key, ai_rec in _ai_perms.items():
                        chk_data = checks.get(chk_key, {})
                        sev      = chk_data.get("severity", "OK")
                        # Build a rich per-column rationale from the audit data
                        base_reason = _rationale.get(chk_key, "")
                        chk_found   = chk_data.get("found", False)
                        chk_hint    = chk_data.get("suggestion", "")
                        detail_parts = []
                        if base_reason:
                            detail_parts.append(base_reason)
                        if chk_hint and chk_hint != base_reason:
                            detail_parts.append(chk_hint)
                        if not detail_parts and chk_found:
                            detail_parts.append("Issue detected in your dataset — review before applying.")
                        full_reason = " ".join(detail_parts)
                        _enriched.append({
                            "key":    chk_key,
                            "label":  chk_data.get("label", chk_key.replace("_"," ").title()),
                            "reason": full_reason,
                            "sev":    sev,
                            "ord":    _SEV_ORDER.get(sev, 9),
                            "ai_rec": ai_rec,
                        })
                    # AI-approved first, then skipped; within each group sort by severity
                    _enriched.sort(key=lambda x: (0 if x["ai_rec"] else 1, x["ord"]))

                    # ── Live approved count for summary bar ────────────
                    n_total    = len(_enriched)
                    n_approved = sum(
                        1 for e in _enriched
                        if st.session_state.get(f"perm_{e['key']}", e["ai_rec"])
                    )
                    n_skipped  = n_total - n_approved
                    pct_w      = int(n_approved / n_total * 100) if n_total else 0
                    bar_c      = "#00e5a0" if n_approved == n_total else ("#ffb347" if n_approved > 0 else "#ff4444")

                    # ── Summary bar ────────────────────────────────────
                    st.markdown(f"""
                    <div style='background:#0c1014;border:1px solid #1c2a35;border-radius:6px;
                        padding:0.9rem 1.2rem;margin:0.8rem 0 1.2rem;'>
                        <div style='display:flex;align-items:center;margin-bottom:0.6rem;'>
                            <span style='font-family:"JetBrains Mono",monospace;font-size:0.62rem;
                                color:#4a6070;letter-spacing:0.12em;text-transform:uppercase;'>
                                AI Cleaning Plan
                            </span>
                            <span style='margin-left:auto;font-family:"JetBrains Mono",monospace;
                                font-size:0.65rem;font-weight:600;color:{bar_c};'>
                                {n_approved} approved
                                <span style='color:#4a6070;font-weight:400;'>
                                &nbsp;·&nbsp; {n_skipped} skipped &nbsp;·&nbsp; {n_total} total
                                </span>
                            </span>
                        </div>
                        <div style='background:#1c2a35;border-radius:3px;height:4px;overflow:hidden;'>
                            <div style='background:{bar_c};width:{pct_w}%;height:100%;border-radius:3px;'></div>
                        </div>
                        <div style='font-family:"JetBrains Mono",monospace;font-size:0.61rem;
                            color:#4a6070;margin-top:0.55rem;line-height:1.5;'>
                            Approving a card here writes directly to
                            <b style='color:#dce8f0;'>Data Fixes</b> — one source of truth.
                            Toggle any card to override the AI recommendation.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Card renderer ──────────────────────────────────
                    def _ai_card(entry, col_ctx):
                        chk_key  = entry["key"]
                        label    = entry["label"]
                        reason   = entry["reason"]
                        sev      = entry["sev"]
                        ai_rec   = entry["ai_rec"]
                        meta     = _SEV_META.get(sev, _SEV_META["OK"])
                        sev_c    = meta["c"]
                        sev_bg   = meta["bg"]

                        # Read live state — default to AI recommendation
                        perm_key = f"perm_{chk_key}"
                        is_on    = st.session_state.get(perm_key, ai_rec)
                        border_c = sev_c if is_on else "#1c2a35"
                        opacity  = "1" if is_on else "0.52"

                        ai_badge_c  = "#00e5a0" if ai_rec else "#ff6060"
                        ai_badge_bg = "#061a10" if ai_rec else "#1a0606"
                        ai_badge_t  = "AI: Apply" if ai_rec else "AI: Skip"
                        override    = is_on != ai_rec
                        ov_html     = (
                            "<span style='font-size:0.52rem;color:#c084fc;"
                            "border:1px solid #c084fc44;padding:1px 5px;"
                            "border-radius:3px;white-space:nowrap;'>overridden</span>"
                            if override else ""
                        )

                        with col_ctx:
                            st.markdown(f"""
                            <div style='background:{sev_bg};border:1px solid {border_c};
                                border-top:2px solid {border_c};border-radius:6px;
                                padding:1.2rem 1.3rem;margin-bottom:0.3rem;opacity:{opacity};'>
                                <div style='display:flex;align-items:flex-start;gap:0.5rem;
                                    margin-bottom:0.5rem;flex-wrap:wrap;'>
                                    <span style='font-family:"Syne",sans-serif;font-size:1rem;
                                        font-weight:800;font-style:normal;line-height:1.4;
                                        letter-spacing:0.01em;color:#dce8f0 !important;
                                        text-decoration:none !important;flex:1;'>{label.replace(chr(32),chr(160))}</span>
                                    <span style='font-family:"JetBrains Mono",monospace;font-size:0.52rem;
                                        color:{sev_c};border:1px solid {sev_c}44;
                                        padding:1px 6px;border-radius:3px;white-space:nowrap;flex-shrink:0;'>{sev}</span>
                                </div>
                                <div style='display:flex;align-items:center;gap:0.5rem;
                                    margin-bottom:0.55rem;flex-wrap:wrap;'>
                                    <span style='font-family:"JetBrains Mono",monospace;font-size:0.55rem;
                                        color:{ai_badge_c};background:{ai_badge_bg};
                                        border:1px solid {ai_badge_c}44;padding:2px 8px;
                                        border-radius:3px;white-space:nowrap;'>🤖 {ai_badge_t}</span>
                                    {ov_html}
                                </div>
                                <div style='font-family:"JetBrains Mono",monospace;font-size:0.63rem;
                                    color:#4a6070;line-height:1.55;'>{reason}</div>
                            </div>
                            """, unsafe_allow_html=True)

                            checked = st.checkbox(
                                "Apply this fix",
                                value=ai_rec,
                                key=perm_key,
                                label_visibility="collapsed",
                            )
                            st.markdown("<div style='margin-bottom:0.6rem;'></div>",
                                        unsafe_allow_html=True)

                    # ── Section: AI recommends APPLYING ───────────────
                    _yes = [e for e in _enriched if e["ai_rec"]]
                    if _yes:
                        for _grp_sev, _grp_label, _grp_c in [
                            ("HIGH",   "🔴  High Severity",   "#ff4444"),
                            ("MEDIUM", "🟡  Medium Severity", "#ffb347"),
                            ("LOW",    "🔵  Low Severity",    "#7eb8f7"),
                            ("OK",     "🟢  Passed",          "#00e5a0"),
                        ]:
                            _grp = [e for e in _yes if e["sev"] == _grp_sev]
                            if not _grp:
                                continue
                            st.markdown(
                                f"<div style='font-family:monospace;font-size:0.58rem;"
                                f"color:{_grp_c};letter-spacing:0.1em;text-transform:uppercase;"
                                f"margin:0.6rem 0 0.4rem;border-left:2px solid {_grp_c}55;"
                                f"padding-left:0.5rem;'>{_grp_label}</div>",
                                unsafe_allow_html=True
                            )
                            _gcols = st.columns(2)
                            for gi, entry in enumerate(_grp):
                                _ai_card(entry, _gcols[gi % 2])

                    # ── Section: AI recommends SKIPPING ───────────────
                    _no = [e for e in _enriched if not e["ai_rec"]]
                    if _no:
                        with st.expander(
                            f"⏭  AI recommends skipping  ({len(_no)})",
                            expanded=False
                        ):
                            st.markdown(
                                "<div style='font-family:monospace;font-size:0.64rem;"
                                "color:#4a6070;margin-bottom:0.8rem;line-height:1.6;'>"
                                "The AI judged these fixes unnecessary for your dataset. "
                                "You can still approve them manually if you disagree.</div>",
                                unsafe_allow_html=True
                            )
                            _ncols = st.columns(2)
                            for ni, entry in enumerate(_no):
                                _ai_card(entry, _ncols[ni % 2])

            # ── INNER TAB 2 — FEATURE ENGINEERING ─────────────
            with ai_inner_tab2:
                st.markdown(
                    "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.65rem;"
                    "color:#4a6070;letter-spacing:0.15em;text-transform:uppercase;"
                    "margin:1rem 0 0.4rem;'>◈ Feature Engineering Suggestions</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.72rem;"
                    "color:#4a6070;margin-bottom:1rem;line-height:1.6;'>New columns you can derive "
                    "from your existing data. Approved features will be created when you apply fixes.</div>",
                    unsafe_allow_html=True
                )

                # Build feature engineering suggestions from df_raw columns
                col_names    = list(df_raw.columns)
                col_types    = {c: _real_type(df_raw[c]) for c in col_names}
                numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
                date_cols    = [c for c in col_names if any(k in c.lower() for k in
                               ("date", "time", "day", "month", "year", "created", "updated"))]
                cat_cols     = [c for c, t in col_types.items() if t == "text"]

                fe_suggestions = []

                # Date-based features
                for dc in date_cols:
                    fe_suggestions += [
                        {"name": f"{dc}_year",      "formula": f"Extract year from '{dc}'",
                         "type": "📅 Date", "color": "#7eb8f7", "bg": "#0a1420"},
                        {"name": f"{dc}_month",     "formula": f"Extract month number (1-12) from '{dc}'",
                         "type": "📅 Date", "color": "#7eb8f7", "bg": "#0a1420"},
                        {"name": f"{dc}_is_weekend","formula": f"1 if '{dc}' falls on Sat/Sun, else 0",
                         "type": "📅 Date", "color": "#7eb8f7", "bg": "#0a1420"},
                        {"name": f"{dc}_quarter",   "formula": f"Quarter number (1-4) from '{dc}'",
                         "type": "📅 Date", "color": "#7eb8f7", "bg": "#0a1420"},
                    ]

                # Math features (ratios / products between numeric pairs)
                price_cols = [c for c in numeric_cols if any(k in c.lower() for k in
                             ("price", "cost", "spend", "spent", "amount", "revenue", "sales", "total"))]
                qty_cols   = [c for c in numeric_cols if any(k in c.lower() for k in
                             ("qty", "quantity", "count", "units", "volume", "num"))]

                if price_cols and qty_cols:
                    pc, qc = price_cols[0], qty_cols[0]
                    fe_suggestions += [
                        {"name": f"avg_unit_price",      "formula": f"'{pc}' / '{qc}' (avg price per unit)",
                         "type": "🔢 Math", "color": "#00e5a0", "bg": "#061a10"},
                        {"name": f"total_value_flag",    "formula": f"1 if '{pc}' > median of '{pc}', else 0",
                         "type": "🔢 Math", "color": "#00e5a0", "bg": "#061a10"},
                    ]

                if len(numeric_cols) >= 2:
                    c1, c2 = numeric_cols[0], numeric_cols[1]
                    fe_suggestions.append(
                        {"name": f"{c1}_to_{c2}_ratio", "formula": f"'{c1}' / ('{c2}' + 1e-9)",
                         "type": "🔢 Math", "color": "#00e5a0", "bg": "#061a10"}
                    )

                # Category features
                for cc in cat_cols[:4]:
                    n_unique = df_raw[cc].nunique()
                    if 2 <= n_unique <= 30:
                        fe_suggestions.append(
                            {"name": f"{cc}_encoded", "formula": f"Label-encode '{cc}' ({n_unique} categories → integers)",
                             "type": "🏷️ Category", "color": "#c084fc", "bg": "#120a1a"}
                        )
                    if n_unique <= 10:
                        fe_suggestions.append(
                            {"name": f"{cc}_freq",    "formula": f"Frequency count of each value in '{cc}'",
                             "type": "🏷️ Category", "color": "#c084fc", "bg": "#120a1a"}
                        )

                # ── FE summary bar ─────────────────────────────────
                if fe_suggestions:
                    n_fe_total   = min(len(fe_suggestions), 12)
                    n_fe_on      = sum(
                        1 for f in fe_suggestions[:12]
                        if st.session_state.get(f"fe_{f['name']}",
                           st.session_state.fe_approved.get(f["name"], False))
                    )
                    fe_bar_c = "#c084fc" if n_fe_on > 0 else "#4a6070"
                    fe_pct_w = int(n_fe_on / n_fe_total * 100) if n_fe_total else 0
                    st.markdown(f"""
                    <div style='background:#0c1014;border:1px solid #1c2a35;border-radius:6px;
                        padding:0.8rem 1.2rem;margin:0.5rem 0 1rem;'>
                        <div style='display:flex;align-items:center;margin-bottom:0.55rem;'>
                            <span style='font-family:monospace;font-size:0.62rem;
                                color:#4a6070;letter-spacing:0.12em;text-transform:uppercase;'>
                                Auto-detected Suggestions
                            </span>
                            <span style='margin-left:auto;font-family:monospace;
                                font-size:0.65rem;font-weight:600;color:{fe_bar_c};'>
                                {n_fe_on} selected
                                <span style='color:#4a6070;font-weight:400;'> / {n_fe_total}</span>
                            </span>
                        </div>
                        <div style='background:#1c2a35;border-radius:3px;height:4px;overflow:hidden;'>
                            <div style='background:{fe_bar_c};width:{fe_pct_w}%;height:100%;border-radius:3px;'></div>
                        </div>
                        <div style='font-family:monospace;font-size:0.6rem;color:#4a6070;margin-top:0.5rem;'>
                            These are rule-based suggestions derived from your column names and types —
                            not generated by the AI. Approved features are created when you apply fixes.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Group by type ───────────────────────────────────
                    _fe_groups = {}
                    for feat in fe_suggestions[:12]:
                        _fe_groups.setdefault(feat["type"], []).append(feat)

                    for _ftype, _flist in _fe_groups.items():
                        _ft_color = _flist[0]["color"]
                        st.markdown(
                            f"<div style='font-family:monospace;font-size:0.58rem;"
                            f"color:{_ft_color};letter-spacing:0.1em;text-transform:uppercase;"
                            f"margin:0.5rem 0 0.4rem;border-left:2px solid {_ft_color}55;"
                            f"padding-left:0.5rem;'>{_ftype}</div>",
                            unsafe_allow_html=True
                        )
                        fe_card_cols = st.columns(2)
                        for fi, feat in enumerate(_flist):
                            with fe_card_cols[fi % 2]:
                                fe_key   = f"fe_{feat['name']}"
                                prev_val = st.session_state.fe_approved.get(feat["name"], False)
                                is_on    = st.session_state.get(fe_key, prev_val)
                                border_c = feat["color"] if is_on else "#1c2a35"
                                opacity  = "1" if is_on else "0.55"

                                # ── Sample preview values ───────────────
                                preview_html = ""
                                try:
                                    if "year" in feat["name"] or "month" in feat["name"] or                                        "quarter" in feat["name"] or "is_weekend" in feat["name"]:
                                        src_col = feat["name"].rsplit("_", 1 if "is_weekend" not in feat["name"] else 0)[0]
                                        # find the actual date col
                                        for dc in date_cols:
                                            if feat["name"].startswith(dc):
                                                src_col = dc
                                                break
                                        if src_col in df_raw.columns:
                                            parsed = pd.to_datetime(df_raw[src_col], errors="coerce").dropna()
                                            if len(parsed):
                                                if "year"    in feat["name"]: vals = parsed.dt.year.dropna().unique()[:4]
                                                elif "month" in feat["name"]: vals = parsed.dt.month.dropna().unique()[:4]
                                                elif "quarter" in feat["name"]: vals = parsed.dt.quarter.dropna().unique()[:4]
                                                elif "is_weekend" in feat["name"]: vals = parsed.dt.dayofweek.apply(lambda d: 1 if d>=5 else 0).unique()[:4]
                                                else: vals = []
                                                if len(vals):
                                                    preview_html = " ".join(
                                                        f"<span style='background:#111820;border:1px solid #1c2a35;"
                                                        f"border-radius:3px;padding:1px 7px;"
                                                        f"font-size:0.6rem;color:{feat['color']};'>{v}</span>"
                                                        for v in vals
                                                    )
                                    elif "_encoded" in feat["name"]:
                                        src_col = feat["name"].replace("_encoded","")
                                        if src_col in df_raw.columns:
                                            cats = df_raw[src_col].dropna().astype(str).unique()[:4]
                                            enc  = {c: i for i, c in enumerate(sorted(cats))}
                                            preview_html = " ".join(
                                                f"<span style='background:#111820;border:1px solid #1c2a35;"
                                                f"border-radius:3px;padding:1px 7px;"
                                                f"font-size:0.6rem;color:{feat['color']};'>{c}→{enc[c]}</span>"
                                                for c in list(enc.keys())[:3]
                                            )
                                    elif "_freq" in feat["name"]:
                                        src_col = feat["name"].replace("_freq","")
                                        if src_col in df_raw.columns:
                                            vc = df_raw[src_col].value_counts().head(3)
                                            preview_html = " ".join(
                                                f"<span style='background:#111820;border:1px solid #1c2a35;"
                                                f"border-radius:3px;padding:1px 7px;"
                                                f"font-size:0.6rem;color:{feat['color']};'>{v}:{n}</span>"
                                                for v, n in vc.items()
                                            )
                                    elif "_ratio" in feat["name"] or feat["name"] in ("avg_unit_price","total_value_flag"):
                                        parts = [p for p in feat["name"].split("_to_") if p]
                                        c1 = parts[0] if parts[0] in df_raw.columns else None
                                        c2 = parts[1].replace("_ratio","") if len(parts)>1 and parts[1].replace("_ratio","") in df_raw.columns else None
                                        if feat["name"] == "avg_unit_price" and price_cols and qty_cols:
                                            c1, c2 = price_cols[0], qty_cols[0]
                                        if c1 and c2 and c1 in df_raw.columns and c2 in df_raw.columns:
                                            s1 = pd.to_numeric(df_raw[c1], errors="coerce")
                                            s2 = pd.to_numeric(df_raw[c2], errors="coerce")
                                            ratio = (s1 / (s2.replace(0, float("nan")))).dropna().round(2)
                                            vals  = ratio.head(3).tolist()
                                            if vals:
                                                preview_html = " ".join(
                                                    f"<span style='background:#111820;border:1px solid #1c2a35;"
                                                    f"border-radius:3px;padding:1px 7px;"
                                                    f"font-size:0.6rem;color:{feat['color']};'>{v}</span>"
                                                    for v in vals
                                                )
                                except Exception:
                                    preview_html = ""

                                preview_block = (
                                    f"<div style='margin-top:0.5rem;line-height:2;'>{preview_html}</div>"
                                    if preview_html else ""
                                )

                                st.markdown(f"""
                                <div style='background:{feat["bg"]};border:1px solid {border_c};
                                    border-top:2px solid {border_c};border-radius:6px;
                                    padding:1.2rem 1.3rem;margin-bottom:0.3rem;opacity:{opacity};'>
                                    <div style='display:flex;align-items:flex-start;gap:0.5rem;margin-bottom:0.5rem;'>
                                        <span style='font-family:"Syne",sans-serif;font-size:1rem;
                                            font-weight:800;font-style:normal;line-height:1.4;
                                            letter-spacing:0.01em;color:#dce8f0 !important;
                                            text-decoration:none !important;flex:1;'>{feat['name'].replace(chr(32),chr(160))}</span>
                                        <span style='font-family:monospace;font-size:0.53rem;
                                            color:{feat["color"]};border:1px solid {feat["color"]}44;
                                            padding:1px 6px;border-radius:3px;white-space:nowrap;
                                            flex-shrink:0;'>{feat["type"]}</span>
                                    </div>
                                    <div style='font-family:monospace;font-size:0.63rem;
                                        color:#4a6070;line-height:1.4;margin-bottom:0.2rem;'>
                                        {feat["formula"]}
                                    </div>
                                    {preview_block}
                                </div>
                                """, unsafe_allow_html=True)
                                fe_checked = st.checkbox("create", value=prev_val, key=fe_key,
                                                          label_visibility="collapsed")
                                st.session_state.fe_approved[feat["name"]] = fe_checked
                                st.markdown("<div style='margin-bottom:0.5rem;'></div>",
                                            unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style='text-align:center;padding:2.5rem 1rem;'>
                        <div style='font-size:2rem;margin-bottom:0.8rem;'>📊</div>
                        <div style='font-family:"Syne",sans-serif;font-size:0.95rem;font-weight:800;
                            color:#4a6070;margin-bottom:0.4rem;'>No suggestions available</div>
                        <div style='font-family:"JetBrains Mono",monospace;font-size:0.7rem;color:#2a3a42;'>
                            Upload a dataset with numeric or date columns for feature engineering ideas.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        else:
            # ── Empty state ────────────────────────────────────
            st.markdown("""
            <div style='text-align:center;padding:3rem 1rem;'>
                <div style='font-size:3rem;margin-bottom:0.8rem;'>🤖</div>
                <div style='font-family:"Syne",sans-serif;font-size:1.1rem;font-weight:800;
                    color:#dce8f0;margin-bottom:0.8rem;'>No AI Strategy Yet</div>
                <div style='font-family:"JetBrains Mono",monospace;font-size:0.75rem;
                    color:#4a6070;line-height:1.7;max-width:400px;margin:0 auto;'>
                    Add your Gemini API key in the sidebar, then click
                    <b style='color:#00e5a0;'>Generate AI Strategy</b> above.
                    The AI will analyze your audit report and suggest a full cleaning plan.
                </div>
            </div>
            """, unsafe_allow_html=True)


    # ══════════════════════════════════════════════════════════
    # SUB-TAB 2 — JUNK & NULLS  (4 inner tabs)
    # ══════════════════════════════════════════════════════════
    with sc_tab2:

        # ── Pre-compute column lists once (used across all inner tabs) ──
        numeric_null_cols = []
        text_null_cols    = []
        for _col in null_by_col:
            if _col not in df_raw.columns:
                continue
            if _real_type(df_raw[_col]) == "numeric":
                numeric_null_cols.append(_col)
            else:
                text_null_cols.append(_col)

        total_nulls   = null_check.get("total", 0)
        total_junk    = sum(sum(v.values()) for v in junk_map.values()) if junk_map else 0
        n_num_nulls   = sum(null_by_col[c]["count"] for c in numeric_null_cols if c in null_by_col)
        n_txt_nulls   = sum(null_by_col[c]["count"] for c in text_null_cols   if c in null_by_col)

        # ── Badge helper ────────────────────────────────────────
        def _count_badge(n, color):
            if n == 0:
                return "<span style='font-family:\"JetBrains Mono\",monospace;font-size:0.6rem;" \
                       "color:#2a4a38;border:1px solid #1c2a35;padding:1px 7px;border-radius:10px;'>✓ clean</span>"
            return (f"<span style='font-family:\"JetBrains Mono\",monospace;font-size:0.6rem;"
                    f"color:{color};border:1px solid {color}55;padding:1px 7px;"
                    f"border-radius:10px;'>{n:,} issues</span>")

        # ── 3 inner tabs ─────────────────────────────────────────
        jn_tab1, jn_tab2, jn_tab3 = st.tabs([
            "🧹  Blank Values",
            "🔢  Numeric Fill",
            "🔤  Text Fill",
        ])

        # ════════════════════════════════════════
        # INNER TAB 1 — BLANK VALUES
        # ════════════════════════════════════════
        with jn_tab1:

            if junk_map:
                # Summary banner — same style as numeric/text fill banners
                st.markdown(
                    f"""<div style='background:#1a1008;border:1px solid #ffb34733;
                        border-left:4px solid #ffb347;border-radius:6px;
                        padding:1.2rem 1.5rem;margin:0.8rem 0 1.2rem;'>
                        <div style='font-family:"Syne",sans-serif;font-size:0.95rem;
                            font-weight:800;color:#ffb347;margin-bottom:0.5rem;'>
                            🧹  Placeholder Words Masking Empty Cells
                        </div>
                        <div style='font-family:"JetBrains Mono",monospace;font-size:0.72rem;
                            color:#8a6030;line-height:1.7;'>
                            <b style='color:#ffb347;'>{total_junk:,} cells</b> across
                            <b style='color:#ffb347;'>{len(junk_map)} column(s)</b> contain
                            words like <code style='color:#ffb347;background:#181008;
                            padding:1px 6px;border-radius:3px;'>unknown</code>,
                            <code style='color:#ffb347;background:#181008;padding:1px 6px;
                            border-radius:3px;'>n/a</code>, or
                            <code style='color:#ffb347;background:#181008;padding:1px 6px;
                            border-radius:3px;'>error</code> — these are text stand-ins for
                            missing data. Tick a column to replace those words with a proper
                            <b>null</b> value so they show up correctly in analysis.
                        </div>
                    </div>""",
                    unsafe_allow_html=True
                )

                junk_approve = {}
                junk_cols_layout = st.columns(2)
                for ji, (col, hits) in enumerate(junk_map.items()):
                    total_in_col = sum(hits.values())
                    pct_in_col   = round(total_in_col / max(len(df_raw), 1) * 100, 1)
                    is_num       = _real_type(df_raw[col]) == "numeric"
                    type_c       = "#00b87a" if is_num else "#7eb8f7"
                    type_lbl     = "numeric" if is_num else "text"
                    words_chips  = " ".join(
                        f"<code style='background:#181008;border:1px solid #ffb34730;"
                        f"padding:3px 9px;border-radius:4px;"
                        f"font-size:0.66rem;color:#c09050;'>{w}</code>"
                        for w in list(hits.keys())[:8]
                    )
                    approved_now = st.session_state.get(f"junk_{col}", True)
                    border_top   = "#ffb347" if approved_now else "#1c2a35"
                    card_bg      = "#130f05" if approved_now else "#0f1318"

                    with junk_cols_layout[ji % 2]:
                        st.markdown(f"""
                        <div style='background:{card_bg};border:1px solid #1c2a35;
                            border-top:2px solid {border_top};border-radius:6px;
                            padding:1.4rem 1.6rem;margin-bottom:0.3rem;'>
                            <div style='display:flex;align-items:flex-start;gap:0.6rem;
                                flex-wrap:wrap;margin-bottom:0.5rem;'>
                                <span style='font-family:"Syne",sans-serif;font-size:1rem;
                                    font-weight:800;font-style:normal;line-height:1.4;
                                    letter-spacing:0.01em;color:#dce8f0 !important;
                                    text-decoration:none !important;flex:1;
                                    padding-bottom:0.3rem;'>
                                    {col.replace(chr(32), chr(160))}
                                </span>
                                <span style='font-family:"JetBrains Mono",monospace;font-size:0.58rem;
                                    color:{type_c};border:1px solid {type_c}33;
                                    padding:2px 7px;border-radius:4px;flex-shrink:0;'>{type_lbl}</span>
                            </div>
                            <div style='font-family:"JetBrains Mono",monospace;font-size:0.65rem;
                                color:#6a5030;margin-bottom:0.7rem;'>
                                {total_in_col:,} cells &nbsp;·&nbsp; {pct_in_col}% of rows
                                &nbsp;·&nbsp; Replace with <b style='color:#ffb347;'>null</b>
                            </div>
                            <div style='line-height:2.2;margin-bottom:0.5rem;'>{words_chips}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        junk_approve[col] = st.checkbox(
                            "→ Replace placeholder words with blank (null)",
                            value=True,
                            key=f"junk_{col}",
                        )
                        st.markdown("<div style='margin-bottom:0.9rem;'></div>", unsafe_allow_html=True)

                st.session_state.junk_approve = junk_approve

            else:
                st.markdown("""
                <div style='text-align:center;padding:3rem 1rem;'>
                    <div style='font-size:2rem;margin-bottom:0.8rem;'>✅</div>
                    <div style='font-family:"Syne",sans-serif;font-size:0.9rem;font-weight:800;
                        color:#00e5a0;'>No blank-value placeholders found</div>
                    <div style='font-family:"JetBrains Mono",monospace;font-size:0.68rem;
                        color:#4a6070;margin-top:0.3rem;'>All cells contain real data or proper null values.</div>
                </div>
                """, unsafe_allow_html=True)

        # ════════════════════════════════════════
        # INNER TAB 2 — NUMERIC FILL
        # ════════════════════════════════════════
        with jn_tab2:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.65rem;"
                "color:#4a6070;letter-spacing:0.15em;text-transform:uppercase;"
                "margin-bottom:0.8rem;margin-top:0.5rem;'>◈ Number columns with empty cells — choose fill method</div>",
                unsafe_allow_html=True
            )

            if not null_check.get("found") or not numeric_null_cols:
                st.markdown("""
                <div style='text-align:center;padding:2.5rem 1rem;'>
                    <div style='font-size:2.2rem;margin-bottom:0.8rem;'>✅</div>
                    <div style='font-family:"Syne",sans-serif;font-size:0.95rem;font-weight:800;
                        color:#00e5a0;margin-bottom:0.6rem;'>No Numeric Columns Need Filling</div>
                    <div style='font-family:"JetBrains Mono",monospace;font-size:0.72rem;color:#4a6070;'>
                        All numeric columns are complete, or there are no numeric columns with nulls.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Summary banner
                st.markdown(f"""
                <div style='background:#061a10;border:1px solid #00e5a033;
                    border-left:4px solid #00e5a0;border-radius:6px;
                    padding:1.2rem 1.5rem;margin-bottom:1.2rem;'>
                    <div style='font-family:"Syne",sans-serif;font-size:0.95rem;
                        font-weight:800;color:#00e5a0;margin-bottom:0.5rem;'>
                        🔢  Numeric Columns — Smart Imputation
                    </div>
                    <div style='font-family:"JetBrains Mono",monospace;font-size:0.72rem;
                        color:#4a8060;line-height:1.7;'>
                        <b style='color:#00e5a0;'>{n_num_nulls:,} empty cells</b> across
                        <b style='color:#00e5a0;'>{len(numeric_null_cols)} column(s)</b>.
                        The recommended fill is based on column skewness — skewed data uses
                        <b>median</b>, balanced data uses <b>mean</b>. You can also leave a
                        column blank and it will not be touched.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ── 2-column card layout ──────────────────────────────
                num_col_pairs = st.columns(2)
                for ni, col in enumerate(numeric_null_cols):
                    raw_s = df_raw[col].copy()
                    if raw_s.dtype == object:
                        mask_junk = raw_s.astype(str).str.strip().str.lower().isin(JUNK_WORDS)
                        raw_s     = raw_s.where(~mask_junk, other=np.nan)
                        raw_s     = pd.to_numeric(raw_s, errors="coerce")
                    clean_s = raw_s.dropna()
                    if len(clean_s) == 0:
                        continue

                    mean_v   = round(float(clean_s.mean()),   2)
                    median_v = round(float(clean_s.median()), 2)
                    skew_v   = float(clean_s.skew()) if len(clean_s) > 2 else 0
                    null_cnt = int(null_by_col[col]["count"])
                    null_pct = round(null_by_col[col]["pct"], 1)
                    rec      = "median" if abs(skew_v) > 1.0 else "mean"
                    rec_val  = mean_v if rec == "mean" else median_v

                    # Default is "leave blank" — only switch to rec if user already chose something
                    saved_strat = st.session_state.null_fill_strategy.get(col, "leave blank")
                    if saved_strat not in ("mean", "median", "mode", "leave blank"):
                        saved_strat = "leave blank"

                    num_options  = ["leave blank", "mean", "median", "mode"]
                    num_opt_idx  = num_options.index(saved_strat)

                    with num_col_pairs[ni % 2]:
                        st.markdown(f"""
                        <div style='background:#0f1318;border:1px solid #1c2a35;
                            border-top:2px solid #00e5a044;border-radius:6px;
                            padding:1.4rem 1.6rem;margin-bottom:0.4rem;'>
                            <div style='display:flex;align-items:flex-start;gap:0.6rem;
                                flex-wrap:wrap;margin-bottom:0.5rem;'>
                                <span style='font-family:"Syne",sans-serif;font-size:1rem;
                                    font-weight:800;font-style:normal;line-height:1.4;
                                    letter-spacing:0.01em;color:#dce8f0 !important;
                                    text-decoration:none !important;flex:1;
                                    padding-bottom:0.3rem;'>
                                    {col.replace(chr(32), chr(160))}
                                </span>
                                <span style='font-family:"JetBrains Mono",monospace;font-size:0.58rem;
                                    color:#ffb347;border:1px solid #ffb34730;padding:1px 6px;
                                    border-radius:3px;white-space:nowrap;flex-shrink:0;'>
                                    {null_cnt:,} empty · {null_pct}%
                                </span>
                            </div>
                            <div style='font-family:"JetBrains Mono",monospace;font-size:0.65rem;
                                color:#3a6050;line-height:1.6;margin-bottom:0.4rem;'>
                                mean&nbsp;=&nbsp;<b style='color:#8ac8a8;'>{mean_v}</b>
                                &nbsp;&nbsp;median&nbsp;=&nbsp;<b style='color:#8ac8a8;'>{median_v}</b>
                                &nbsp;&nbsp;skew&nbsp;=&nbsp;<b style='color:#8ac8a8;'>{round(skew_v,2)}</b>
                                &nbsp;&nbsp;💡 recommended:&nbsp;<b style='color:#00e5a0;'>{rec}</b>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        choice = st.radio(
                            f"Fill strategy for {col}",
                            options=num_options,
                            index=num_opt_idx,
                            key=f"numradio_{col}",
                            horizontal=True,
                            label_visibility="collapsed",
                        )
                        if choice == "leave blank":
                            st.markdown(
                                "<div style='font-family:\"JetBrains Mono\",monospace;"
                                "font-size:0.65rem;color:#4a6070;margin-top:2px;'>"
                                "↳ Column will not be touched — empty cells stay empty.</div>",
                                unsafe_allow_html=True
                            )
                        else:
                            fill_preview = mean_v if choice == "mean" else (median_v if choice == "median" else "most frequent")
                            st.markdown(
                                f"<div style='font-family:\"JetBrains Mono\",monospace;"
                                f"font-size:0.65rem;color:#00e5a0;margin-top:2px;'>"
                                f"↳ Will fill {null_cnt:,} cells with <b>{choice}</b>"
                                f"{f' = {fill_preview}' if choice != 'mode' else ''}.</div>",
                                unsafe_allow_html=True
                            )
                        st.session_state.null_fill_strategy[col] = choice
                        st.markdown("<div style='margin-bottom:0.8rem;'></div>", unsafe_allow_html=True)

        # ════════════════════════════════════════
        # INNER TAB 3 — TEXT FILL
        # ════════════════════════════════════════
        with jn_tab3:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.65rem;"
                "color:#4a6070;letter-spacing:0.15em;text-transform:uppercase;"
                "margin-bottom:0.8rem;margin-top:0.5rem;'>◈ Text columns with empty cells — choose fill value</div>",
                unsafe_allow_html=True
            )

            if not null_check.get("found") or not text_null_cols:
                st.markdown("""
                <div style='text-align:center;padding:2.5rem 1rem;'>
                    <div style='font-size:2.2rem;margin-bottom:0.8rem;'>✅</div>
                    <div style='font-family:"Syne",sans-serif;font-size:0.95rem;font-weight:800;
                        color:#00e5a0;margin-bottom:0.6rem;'>No Text Columns Need Filling</div>
                    <div style='font-family:"JetBrains Mono",monospace;font-size:0.72rem;color:#4a6070;'>
                        All text columns are complete, or there are no text columns with nulls.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background:#0a1420;border:1px solid #7eb8f733;
                    border-left:4px solid #7eb8f7;border-radius:6px;
                    padding:1.2rem 1.5rem;margin-bottom:1.2rem;'>
                    <div style='font-family:"Syne",sans-serif;font-size:0.95rem;
                        font-weight:800;color:#7eb8f7;margin-bottom:0.5rem;'>
                        🔤  Text Columns — Fill with Known Value
                    </div>
                    <div style='font-family:"JetBrains Mono",monospace;font-size:0.72rem;
                        color:#4a6080;line-height:1.7;'>
                        <b style='color:#7eb8f7;'>{n_txt_nulls:,} empty cells</b> across
                        <b style='color:#7eb8f7;'>{len(text_null_cols)} column(s)</b>.
                        Pick the most common value from real data, type a fixed label, or
                        leave a column blank — empty cells will stay as-is.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ── 2-column card layout ──────────────────────────────
                txt_col_pairs = st.columns(2)
                for ti, col in enumerate(text_null_cols):
                    null_cnt = int(null_by_col[col]["count"])
                    null_pct = round(null_by_col[col]["pct"], 1)
                    top_vals = (
                        df_raw[col].dropna()
                        .astype(str).str.strip()
                        .pipe(lambda s: s[~s.str.lower().isin(JUNK_WORDS)])
                        .value_counts().head(6).index.tolist()
                    )
                    unique_count = df_raw[col].nunique()

                    # Default is "leave blank"
                    current_strat = st.session_state.null_fill_strategy.get(col, "leave empty")
                    if current_strat == "leave empty":
                        radio_idx = 0
                    elif current_strat in top_vals:
                        radio_idx = 1
                    elif current_strat.startswith("custom:"):
                        radio_idx = 2
                    else:
                        radio_idx = 0

                    txt_options = ["Leave blank (null)", "Most common value", "Type my own value"]

                    with txt_col_pairs[ti % 2]:
                        st.markdown(f"""
                        <div style='background:#0f1318;border:1px solid #1c2a35;
                            border-top:2px solid #7eb8f744;border-radius:6px;
                            padding:1.4rem 1.6rem;margin-bottom:0.4rem;'>
                            <div style='display:flex;align-items:flex-start;gap:0.6rem;
                                flex-wrap:wrap;margin-bottom:0.5rem;'>
                                <span style='font-family:"Syne",sans-serif;font-size:1rem;
                                    font-weight:800;font-style:normal;line-height:1.4;
                                    letter-spacing:0.01em;color:#dce8f0 !important;
                                    text-decoration:none !important;flex:1;
                                    padding-bottom:0.3rem;'>
                                    {col.replace(chr(32), chr(160))}
                                </span>
                                <span style='font-family:"JetBrains Mono",monospace;font-size:0.58rem;
                                    color:#ffb347;border:1px solid #ffb34730;padding:1px 6px;
                                    border-radius:3px;white-space:nowrap;flex-shrink:0;'>
                                    {null_cnt:,} empty · {null_pct}%
                                </span>
                            </div>
                            <div style='font-family:"JetBrains Mono",monospace;font-size:0.65rem;
                                color:#3a5070;line-height:1.6;margin-bottom:0.4rem;'>
                                {unique_count} unique values
                                {"&nbsp;&nbsp;·&nbsp;&nbsp;top: " + " &nbsp;·&nbsp; ".join(f'<b style="color:#7eb8f7;">{v}</b>' for v in top_vals[:3]) if top_vals else ""}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        txt_radio = st.radio(
                            f"Fill strategy for {col}",
                            options=txt_options,
                            index=radio_idx,
                            key=f"txtradio_{col}",
                            horizontal=True,
                            label_visibility="collapsed",
                        )

                        if "Leave blank" in txt_radio:
                            st.markdown(
                                "<div style='font-family:\"JetBrains Mono\",monospace;"
                                "font-size:0.65rem;color:#4a6070;margin-top:2px;'>"
                                "↳ Column will not be touched — empty cells stay empty.</div>",
                                unsafe_allow_html=True
                            )
                            st.session_state.null_fill_strategy[col] = "leave empty"

                        elif "Most common" in txt_radio:
                            if top_vals:
                                pick = st.selectbox(
                                    "pick value",
                                    options=top_vals,
                                    key=f"txt_pick_{col}",
                                    label_visibility="collapsed",
                                )
                                st.session_state.null_fill_strategy[col] = pick
                                st.markdown(
                                    f"<div style='font-family:\"JetBrains Mono\",monospace;"
                                    f"font-size:0.65rem;color:#00e5a0;margin-top:2px;'>"
                                    f"↳ Will fill {null_cnt:,} cells with <b>\"{pick}\"</b>.</div>",
                                    unsafe_allow_html=True
                                )
                            else:
                                st.warning("No real values found in this column.")
                                st.session_state.null_fill_strategy[col] = "leave empty"

                        elif "Type my own" in txt_radio:
                            if top_vals:
                                st.markdown(
                                    "<div style='font-family:\"JetBrains Mono\",monospace;"
                                    "font-size:0.65rem;color:#4a6070;margin-bottom:4px;'>Suggestions: "
                                    + " &nbsp; ".join(
                                        f"<b style='color:#7eb8f7;'>{v}</b>" for v in top_vals[:4]
                                    ) + "</div>",
                                    unsafe_allow_html=True
                                )
                            custom_val = st.text_input(
                                "custom value",
                                value="" if not current_strat.startswith("custom:") else current_strat[7:],
                                key=f"txt_custom_{col}",
                                placeholder=f'e.g. "{top_vals[0]}"' if top_vals else "type a value…",
                                label_visibility="collapsed",
                            )
                            if custom_val.strip():
                                st.session_state.null_fill_strategy[col] = f"custom:{custom_val.strip()}"
                                st.markdown(
                                    f"<div style='font-family:\"JetBrains Mono\",monospace;"
                                    f"font-size:0.65rem;color:#00e5a0;margin-top:2px;'>"
                                    f"↳ Will fill {null_cnt:,} cells with <b>\"{custom_val.strip()}\"</b>.</div>",
                                    unsafe_allow_html=True
                                )
                            else:
                                st.session_state.null_fill_strategy[col] = "leave empty"

                        st.markdown("<div style='margin-bottom:0.8rem;'></div>", unsafe_allow_html=True)




    # ══════════════════════════════════════════════════════════
    # SUB-TAB 3 — DATA FIXES
    # ══════════════════════════════════════════════════════════
    with sc_tab3:

        permissions   = {}
        any_fixable_3 = False

        def _fix_card(key, check, default_on):
            sev    = check.get("severity", "OK")
            sev_c  = {"HIGH": "#ff4444", "MEDIUM": "#ffb347", "OK": "#00e5a0"}.get(sev, "#4a6070")
            sev_bg = {"HIGH": "#160606", "MEDIUM": "#141008", "OK": "#06120a"}.get(sev, "#0c1014")
            label  = check.get("label", key)
            hint   = check.get("suggestion", "")
            # read current value for border accent
            is_on  = st.session_state.get(f"fix_{key}", default_on)
            border = sev_c if is_on else "#1c2a35"
            st.markdown(f"""
            <div style='background:{sev_bg};border:1px solid {border};
                border-top:2px solid {border};border-radius:6px;
                padding:1.1rem 1.2rem;margin-bottom:0.6rem;min-height:100px;
                display:flex;flex-direction:column;justify-content:space-between;'>
                <div style='display:flex;align-items:flex-start;gap:0.5rem;'>
                    <div style='flex:1;'>
                        <div style='font-family:"Syne",sans-serif;font-size:1rem;font-weight:800;font-style:normal;line-height:1.6;letter-spacing:0.01em;color:#dce8f0 !important;text-decoration:none !important;
                            margin-bottom:{"0.3rem" if hint else "0"};'>{label.replace(chr(32), chr(160))}</div>
                        {"<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;color:#4a6070;line-height:1.4;'>" + hint + "</div>" if hint else ""}
                    </div>
                    <span style='font-family:"JetBrains Mono",monospace;font-size:0.55rem;
                        color:{sev_c};border:1px solid {sev_c}44;padding:1px 6px;
                        border-radius:3px;white-space:nowrap;flex-shrink:0;'>{sev}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            checked = st.checkbox("apply", value=default_on, key=f"fix_{key}",
                                  label_visibility="collapsed")
            permissions[key] = checked
            return checked

        if high_checks:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;"
                "color:#ff6060;letter-spacing:0.12em;text-transform:uppercase;"
                "margin:0.5rem 0 0.6rem;'>🔴 High severity</div>",
                unsafe_allow_html=True
            )
            fix_cols = st.columns(2)
            for ci, (key, check) in enumerate(high_checks.items()):
                with fix_cols[ci % 2]:
                    if _fix_card(key, check, default_on=_ai_perms.get(key, True)):
                        any_fixable_3 = True
            st.markdown("<div style='margin-bottom:0.8rem;'></div>", unsafe_allow_html=True)

        if medium_checks:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;"
                "color:#ffb347;letter-spacing:0.12em;text-transform:uppercase;"
                "margin:0 0 0.6rem;'>🟡 Medium severity</div>",
                unsafe_allow_html=True
            )
            fix_cols2 = st.columns(2)
            for ci, (key, check) in enumerate(medium_checks.items()):
                with fix_cols2[ci % 2]:
                    if _fix_card(key, check, default_on=_ai_perms.get(key, False)):
                        any_fixable_3 = True
            st.markdown("<div style='margin-bottom:0.8rem;'></div>", unsafe_allow_html=True)

        if ok_checks:
            with st.expander("🟢 Passed checks", expanded=False):
                for key, check in ok_checks.items():
                    permissions[key] = False
                    st.markdown(
                        f"<div style='font-family:\"JetBrains Mono\",monospace;"
                        f"font-size:0.7rem;color:#2a4a38;padding:3px 0;'>"
                        f"✓ {check['label']}</div>",
                        unsafe_allow_html=True
                    )

        if not high_checks and not medium_checks:
            st.markdown("""
            <div style='text-align:center;padding:3rem 1rem;'>
                <div style='font-size:2rem;margin-bottom:0.8rem;'>✅</div>
                <div style='font-family:"Syne",sans-serif;font-size:0.95rem;font-weight:800;
                    color:#00e5a0;margin-bottom:0.6rem;'>All Checks Passed</div>
                <div style='font-family:"JetBrains Mono",monospace;font-size:0.7rem;color:#4a6070;'>
                    No structural issues detected.
                </div>
            </div>
            """, unsafe_allow_html=True)

        if null_check.get("found"):
            permissions["nulls"] = True
        for key in checks:
            if key not in permissions:
                permissions[key] = False


    # ══════════════════════════════════════════════════════════
    # SUB-TAB 4 — REVIEW & APPLY
    # ══════════════════════════════════════════════════════════
    with sc_tab4:
        st.markdown(
            "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.65rem;"
            "color:#4a6070;letter-spacing:0.15em;text-transform:uppercase;"
            "margin-bottom:1rem;'>◈ Review all selected operations, then apply</div>",
            unsafe_allow_html=True
        )

        # Rebuild permissions: Data Fixes tab uses fix_{key}, AI Advisor uses perm_{key}.
        # fix_ takes priority (user explicitly touched it); perm_ is the AI suggestion fallback.
        final_permissions = {}
        for key in checks:
            fix_key  = f"fix_{key}"
            ai_key   = f"perm_{key}"
            if fix_key in st.session_state:
                final_permissions[key] = bool(st.session_state[fix_key])
            elif ai_key in st.session_state:
                final_permissions[key] = bool(st.session_state[ai_key])
            elif key == "nulls" and null_check.get("found"):
                final_permissions[key] = True
            else:
                final_permissions[key] = False

        # fix_ and perm_ are separate namespaces — no collision possible.

        # Build summary of all approved operations
        ops_to_run = []

        junk_cols_approved = [c for c, v in st.session_state.get("junk_approve", {}).items() if v]
        if junk_cols_approved:
            ops_to_run.append({
                "icon": "🔍", "color": "#ffb347",
                "text": f"Clear fake-empty values in {len(junk_cols_approved)} column(s): "
                        + ", ".join(f"'{c}'" for c in junk_cols_approved),
            })

        for col, strategy in st.session_state.null_fill_strategy.items():
            if strategy in ("leave empty", "leave blank"):
                continue
            if strategy in ("mean", "median", "mode"):
                ops_to_run.append({"icon": "🩹", "color": "#00e5a0",
                                   "text": f"Fill empty cells in '{col}' with {strategy.upper()}"})
            elif strategy.startswith("custom:"):
                ops_to_run.append({"icon": "🔤", "color": "#7eb8f7",
                                   "text": f"Fill empty cells in '{col}' with: \"{strategy[7:]}\""})
            else:
                ops_to_run.append({"icon": "🔤", "color": "#7eb8f7",
                                   "text": f"Fill empty cells in '{col}' with most common: \"{strategy}\""})

        for k, v in final_permissions.items():
            if v and k in checks and k != "nulls":
                ops_to_run.append({"icon": "🔧", "color": "#00e5a0",
                                   "text": checks[k]["label"]})

        fe_ops = [(n, v) for n, v in st.session_state.get("fe_approved", {}).items() if v]
        for feat_name, _ in fe_ops:
            ops_to_run.append({"icon": "✨", "color": "#c084fc",
                               "text": f"Create feature column: '{feat_name}'"})

        any_fixable = bool(ops_to_run)

        # ── Summary panel ──────────────────────────────────────
        if ops_to_run:
            ops_html = "".join(
                f"<div style='display:flex;align-items:center;gap:0.7rem;padding:7px 0;"
                f"border-bottom:1px solid #1c2a35;'>"
                f"<span style='font-size:1rem;flex-shrink:0;'>{op['icon']}</span>"
                f"<span style='font-family:\"JetBrains Mono\",monospace;font-size:0.73rem;"
                f"color:#dce8f0;'>{op['text']}</span>"
                f"<span style='margin-left:auto;font-family:\"JetBrains Mono\",monospace;"
                f"font-size:0.6rem;color:{op['color']};'>READY</span>"
                f"</div>"
                for op in ops_to_run
            )
            st.markdown(f"""
            <div style='background:#0c1014;border:1px solid #00e5a033;border-radius:6px;
                padding:1.1rem 1.4rem;margin-bottom:1.2rem;'>
                <div style='display:flex;align-items:center;gap:0.6rem;margin-bottom:0.8rem;'>
                    <span style='font-family:"Syne",sans-serif;font-size:0.95rem;font-weight:800;
                        color:#00e5a0;'>✅ {len(ops_to_run)} Operation(s) Ready</span>
                    <span style='margin-left:auto;font-family:"JetBrains Mono",monospace;
                        font-size:0.62rem;color:#4a6070;border:1px solid #1c2a35;
                        padding:2px 10px;border-radius:20px;'>original file unchanged</span>
                </div>
                {ops_html}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='background:#0c1014;border:1px dashed #1c2a35;border-radius:6px;
                padding:2rem;text-align:center;margin-bottom:1.2rem;'>
                <div style='font-size:2rem;margin-bottom:0.8rem;'>📋</div>
                <div style='font-family:"Syne",sans-serif;font-size:0.95rem;font-weight:800;
                    color:#4a6070;margin-bottom:0.7rem;'>Nothing Selected Yet</div>
                <div style='font-family:"JetBrains Mono",monospace;font-size:0.72rem;color:#2a3a42;'>
                    Visit the <b style='color:#dce8f0;'>AI Advisor</b>, <b style='color:#dce8f0;'>Junk Values &amp; Nulls</b>, or <b style='color:#dce8f0;'>Data Fixes</b> tabs, approve the operations you want, then return here to apply them.
                </div>
            </div>
            """, unsafe_allow_html=True)

        clean_btn = st.button(
            "🧹  Apply Selected Fixes",
            use_container_width=True,
            disabled=not any_fixable,
            key="apply_fixes_btn",
        )

        if clean_btn:
            with st.spinner("Cleaning in progress…"):
                try:
                    from data_auditor_v4 import DataCleaner  # type: ignore

                    auditor = st.session_state.get("auditor")
                    if auditor is None:
                        st.error("Please click **🚀 Run Deep Audit** first.")
                        st.stop()

                    cleaner = DataCleaner.from_dataframe(auditor.df, audit_report=report)
                    cleaner.df           = auditor.df.copy()
                    cleaner.original_df  = cleaner.df.copy()
                    cleaner.stats_before = cleaner._stats()

                    # STEP 1: Replace junk words with NaN
                    for col, approved in st.session_state.get("junk_approve", {}).items():
                        if not approved or col not in cleaner.df.columns:
                            continue
                        mask = cleaner.df[col].astype(str).str.strip().str.lower().isin(JUNK_WORDS)
                        n = int(mask.sum())
                        if n > 0:
                            cleaner.df.loc[mask, col] = np.nan
                            cleaner._log(f"Cleared {n} junk-word cells in '{col}' → now empty (NaN)")

                    # STEP 2: Coerce numeric columns that were stored as text
                    for col in (list(null_by_col.keys()) if null_check.get("found") else []):
                        if col in cleaner.df.columns and _real_type(df_raw[col]) == "numeric" and cleaner.df[col].dtype == object:
                            cleaner.df[col] = pd.to_numeric(cleaner.df[col], errors="coerce")

                    # STEP 3: Fill nulls with user strategy
                    fill_strat = st.session_state.null_fill_strategy
                    for col, strategy in fill_strat.items():
                        if col not in cleaner.df.columns or strategy in ("leave empty", "leave blank"):
                            continue
                        null_mask = cleaner.df[col].isnull()
                        if not null_mask.any():
                            continue
                        col_is_numeric = pd.api.types.is_numeric_dtype(cleaner.df[col])
                        if strategy in ("mean", "median", "mode") and col_is_numeric:
                            if strategy == "mean":
                                val = cleaner.df[col].mean()
                            elif strategy == "median":
                                val = cleaner.df[col].median()
                            else:
                                modes = cleaner.df[col].mode()
                                val   = modes.iloc[0] if len(modes) else cleaner.df[col].median()
                            cleaner.df[col] = cleaner.df[col].fillna(val)
                            cleaner._log(f"Filled {null_mask.sum()} empty cells in '{col}' with {strategy} = {round(float(val), 3)}")
                        elif not col_is_numeric:
                            if strategy.startswith("custom:"):
                                fill_val = strategy[7:]
                            elif strategy == "unknown_label":
                                fill_val = "Unknown"
                            else:
                                fill_val = strategy
                            if fill_val:
                                cleaner.df[col] = cleaner.df[col].fillna(fill_val)
                                cleaner._log(f"Filled {null_mask.sum()} empty text cells in '{col}' with \"{fill_val}\"")

                    final_permissions["nulls"] = False

                    # STEP 4: Standard fixes
                    cleaner.run(final_permissions, skew_threshold=skew_threshold)

                    # STEP 5: Feature Engineering
                    for feat_name, approved_fe in st.session_state.get("fe_approved", {}).items():
                        if not approved_fe:
                            continue
                        try:
                            cols = list(cleaner.df.columns)
                            if feat_name.endswith("_year") and any(feat_name[:-5] in c for c in cols):
                                base = [c for c in cols if feat_name[:-5] in c][0]
                                cleaner.df[feat_name] = pd.to_datetime(cleaner.df[base], errors="coerce").dt.year
                                cleaner._log(f"Feature engineering: created '{feat_name}' from '{base}'")
                            elif feat_name.endswith("_month") and any(feat_name[:-6] in c for c in cols):
                                base = [c for c in cols if feat_name[:-6] in c][0]
                                cleaner.df[feat_name] = pd.to_datetime(cleaner.df[base], errors="coerce").dt.month
                                cleaner._log(f"Feature engineering: created '{feat_name}' from '{base}'")
                            elif feat_name.endswith("_is_weekend") and any(feat_name[:-11] in c for c in cols):
                                base = [c for c in cols if feat_name[:-11] in c][0]
                                cleaner.df[feat_name] = pd.to_datetime(cleaner.df[base], errors="coerce").dt.dayofweek.isin([5, 6]).astype(int)
                                cleaner._log(f"Feature engineering: created '{feat_name}' from '{base}'")
                            elif feat_name.endswith("_quarter") and any(feat_name[:-8] in c for c in cols):
                                base = [c for c in cols if feat_name[:-8] in c][0]
                                cleaner.df[feat_name] = pd.to_datetime(cleaner.df[base], errors="coerce").dt.quarter
                                cleaner._log(f"Feature engineering: created '{feat_name}' from '{base}'")
                            elif feat_name.endswith("_encoded"):
                                base = feat_name[:-8]
                                if base in cleaner.df.columns:
                                    cleaner.df[feat_name] = cleaner.df[base].astype("category").cat.codes
                                    cleaner._log(f"Feature engineering: label-encoded '{base}' → '{feat_name}'")
                            elif feat_name.endswith("_freq"):
                                base = feat_name[:-5]
                                if base in cleaner.df.columns:
                                    freq_map = cleaner.df[base].value_counts().to_dict()
                                    cleaner.df[feat_name] = cleaner.df[base].map(freq_map)
                                    cleaner._log(f"Feature engineering: frequency encoded '{base}' → '{feat_name}'")
                            elif "avg_unit_price" in feat_name:
                                price_c = [c for c in cleaner.df.columns if any(k in c.lower() for k in ("price","cost","spend","spent","amount","total"))]
                                qty_c   = [c for c in cleaner.df.columns if any(k in c.lower() for k in ("qty","quantity","count","units"))]
                                if price_c and qty_c:
                                    cleaner.df[feat_name] = cleaner.df[price_c[0]] / (cleaner.df[qty_c[0]].replace(0, np.nan))
                                    cleaner._log(f"Feature engineering: created '{feat_name}'")
                            elif "ratio" in feat_name:
                                parts = feat_name.split("_to_")
                                if len(parts) == 2:
                                    c1 = parts[0]
                                    c2 = parts[1].replace("_ratio","")
                                    if c1 in cleaner.df.columns and c2 in cleaner.df.columns:
                                        cleaner.df[feat_name] = cleaner.df[c1] / (cleaner.df[c2] + 1e-9)
                                        cleaner._log(f"Feature engineering: created '{feat_name}'")
                        except Exception as fe_err:
                            cleaner._log(f"Feature engineering skipped for '{feat_name}': {fe_err}")

                    st.session_state.clean_df  = cleaner.df.copy()
                    st.session_state.audit_log = cleaner.get_audit_log()

                    _diff = cleaner.diff_report()
                    try:
                        from data_auditor_v4 import FinalReport  # type: ignore
                        _health_after = FinalReport(auditor, cleaner, final_permissions)._rescore()
                    except Exception:
                        _health_after = report["health_score"]

                    _diff["health_after"]  = _health_after
                    _diff["health_before"] = report["health_score"]
                    _diff["grade_after"]   = ("A" if _health_after >= 90 else
                                              "B" if _health_after >= 75 else
                                              "C" if _health_after >= 55 else "D")
                    st.session_state.clean_summary = _diff
                    st.rerun()

                except Exception as e:
                    st.error(f"Cleaning failed: {e}")

        # ── Post-clean results ─────────────────────────────────
        if st.session_state.clean_df is not None:
            diff     = st.session_state.clean_summary
            clean_df = st.session_state.clean_df

            score_before = diff.get("health_before", report["health_score"])
            score_after  = diff.get("health_after",  score_before)
            score_delta  = score_after - score_before
            score_color  = "#00e5a0" if score_delta >= 0 else "#ff4444"
            grade_after  = diff.get("grade_after", "B")

            rows_removed = diff["rows_removed"]
            cols_removed = diff["cols_removed"]
            nulls_fixed  = diff["nulls_fixed"]
            dups_removed = diff["duplicates_removed"]
            nulls_before = diff["before"]["nulls"]
            nulls_after  = diff["after"]["nulls"]

            st.markdown(f"""
            <div class='clean-banner'>
                <div class='clean-banner-icon'>✅</div>
                <div class='clean-banner-text'>
                    <div class='clean-banner-title'>Cleaning Complete!</div>
                    <div class='clean-banner-sub'>
                        Score: <span style='color:#ffb347;font-weight:600;'>{score_before}%</span>
                        → <span style='color:#00e5a0;font-weight:600;'>{score_after}%</span>
                        <span style='color:{score_color};'>({score_delta:+} pts)</span>
                    </div>
                </div>
                <div class='clean-banner-grade'>
                    <div class='clean-banner-grade-val' style='color:{score_color};'>Grade {grade_after}</div>
                    <div class='clean-banner-grade-lbl'>after cleaning</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            pc1, pc2, pc3 = st.columns([1, 8, 1])
            with pc1:
                st.markdown(f"<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.7rem;"
                            f"color:#4a6070;padding-top:8px;text-align:right;'>{score_before}%</div>",
                            unsafe_allow_html=True)
            with pc2:
                st.progress(min(score_after / 100.0, 1.0))
            with pc3:
                st.markdown(f"<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.7rem;"
                            f"color:{score_color};padding-top:8px;'>{score_after}%</div>",
                            unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            def _card(icon, number, title, desc, color, bg):
                return (
                    f"<div class='result-card' "
                    f"style='background:{bg};border:1px solid {color}33;border-top:3px solid {color};'>"
                    f"<div class='result-card-icon'>{icon}</div>"
                    f"<div class='result-card-number' style='color:{color};'>{number}</div>"
                    f"<div class='result-card-title'>{title}</div>"
                    f"<div class='result-card-desc'>{desc}</div>"
                    f"</div>"
                )

            card1 = (_card("🗑️", f"{dups_removed:,}", "Duplicates removed",
                "Exact copies deleted — each record counted once.", "#00e5a0", "#061a10")
                if dups_removed > 0 else
                _card("✅", "0", "No duplicates", "Every row is unique.", "#4a6070", "#0c1014"))

            card2 = (_card("🩹", f"{nulls_fixed:,}", "Empty cells filled",
                f"Was {nulls_before:,} → now {nulls_after:,}.", "#00e5a0", "#061a10")
                if nulls_fixed > 0 else
                (_card("🔍", f"{abs(nulls_fixed):,}", "Hidden bad values exposed",
                f"Was {nulls_before:,} → {nulls_after:,}.", "#ffb347", "#1a1008")
                if nulls_fixed < 0 else
                _card("✅", "0", "Empty cells unchanged", "No imputation needed.", "#4a6070", "#0c1014")))

            card3 = (_card("✂️", f"{rows_removed:,}", "Rows removed",
                f"{diff['after']['rows']:,} clean rows remain.", "#00e5a0", "#061a10")
                if rows_removed > 0 else
                _card("✅", "0", "All rows kept", f"All {diff['after']['rows']:,} records intact.", "#4a6070", "#0c1014"))

            card4 = (_card("🗂️", f"{cols_removed:,}", "Column(s) removed",
                f"{diff['after']['cols']} columns remain.", "#ffb347", "#1a1008")
                if cols_removed > 0 else
                _card("✅", "0", "All columns kept", f"All {diff['after']['cols']} columns passed.", "#4a6070", "#0c1014"))

            st.markdown(f"<div class='result-cards'>{card1}{card2}{card3}{card4}</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            def _row(label, bv, av, lower_better=True):
                changed = bv != av
                if changed:
                    better = (av < bv) if lower_better else (av > bv)
                    ac     = "#00e5a0" if better else "#ffb347"
                    arrow  = "↓" if av < bv else "↑"
                else:
                    ac, arrow = "#4a6070", "→"
                return (
                    f"<div class='ba-row'>"
                    f"<div class='ba-label'>{label}</div>"
                    f"<div class='ba-before'>{bv:,}</div>"
                    f"<div class='ba-arrow'>{arrow}</div>"
                    f"<div class='ba-after' style='color:{ac};'>{av:,}</div>"
                    f"</div>"
                )

            header = (
                "<div class='ba-header'>"
                "<div style='flex:2'></div>"
                "<div style='flex:1;text-align:right;'>Before</div>"
                "<div style='flex:0 0 2rem;'></div>"
                "<div style='flex:1;'>After</div>"
                "</div>"
            )
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.68rem;"
                "color:#4a6070;letter-spacing:0.12em;text-transform:uppercase;"
                "margin-bottom:0.8rem;'>◈ Before vs After</div>",
                unsafe_allow_html=True
            )
            st.markdown(
                f"<div class='ba-table'>{header}"
                f"{_row('Total rows',    diff['before']['rows'],       diff['after']['rows'],       lower_better=False)}"
                f"{_row('Total columns', diff['before']['cols'],       diff['after']['cols'],       lower_better=False)}"
                f"{_row('Empty cells',   nulls_before,                 nulls_after,                 lower_better=True)}"
                f"{_row('Duplicates',    diff['before']['duplicates'], diff['after']['duplicates'], lower_better=True)}"
                f"</div>",
                unsafe_allow_html=True
            )

            st.markdown("---")

            with st.expander(f"📋 Operations log ({len(st.session_state.audit_log)} steps)", expanded=False):
                for i, entry in enumerate(st.session_state.audit_log):
                    st.markdown(
                        f"<div style='font-family:\"JetBrains Mono\",monospace;"
                        f"font-size:0.71rem;color:#4a6070;padding:2px 0;"
                        f"border-bottom:1px solid #1c2a35;'>"
                        f"<span style='color:#2a4a38;margin-right:0.5rem;'>{i+1:02d}</span>"
                        f"{entry}</div>",
                        unsafe_allow_html=True
                    )

            st.markdown(
                "<span style='font-family:\"JetBrains Mono\",monospace;font-size:.7rem;"
                "color:#00e5a0;letter-spacing:.15em;text-transform:uppercase;'>◈ Cleaned Data Preview</span>",
                unsafe_allow_html=True
            )
            st.dataframe(clean_df.head(20), use_container_width=True)

            st.markdown("---")
            dl1, dl2 = st.columns(2)
            with dl1:
                csv_buf = io.StringIO()
                clean_df.to_csv(csv_buf, index=False)
                st.download_button("⬇  Download CSV", csv_buf.getvalue(),
                                   "cleaned_data.csv", "text/csv", use_container_width=True)
            with dl2:
                xl_buf = io.BytesIO()
                clean_df.to_excel(xl_buf, index=False, engine="openpyxl")
                xl_buf.seek(0)
                st.download_button("⬇  Download Excel", xl_buf.getvalue(),
                                   "cleaned_data.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)



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
                f"border-radius:4px;padding:2px 10px;font-family:\"JetBrains Mono\",monospace;"
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
                # BUG FIX: use from_dataframe()
                _auditor = st.session_state.get("auditor")
                if _auditor is None:
                    st.error("Auditor not found. Please click **🚀 Run Deep Audit** again first.")
                    st.stop()
                priv_cleaner = DataCleaner.from_dataframe(_auditor.df, audit_report=report)
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
        "<div style='width:60px;height:2px;background:#00e5a0;margin-bottom:0.7rem;'></div>",
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
        f"<small style='color:#4a6070;'>Source: {src_label} &nbsp;·&nbsp; "
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
    import html as _Hesc
    import io as _io

    def _E(v): return _Hesc.escape(str(v or ""))

    # ── helpers ──────────────────────────────────────────────────
    def _sec(icon, text, color="#00e5a0"):
        return (
            f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.6rem;"
            f"color:{color};letter-spacing:0.16em;text-transform:uppercase;"
            f"margin:0.6rem 0 0.4rem;border-left:2px solid {color}55;padding-left:0.6rem;"
            f"\">{icon} {_E(text)}</div>"
        )

    def _kpi_card(label, value, color="#00e5a0", sub=""):
        sub_html = f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.6rem;color:#4a6070;margin-top:0.25rem;\">{_E(sub)}</div>" if sub else ""
        return (
            f"<div class=\"anim-up\" style=\"background:#0c1014;border:1px solid #1c2a35;"
            f"border-top:2px solid {color};border-radius:8px;padding:1rem 1.2rem;\">"
            f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.58rem;"
            f"color:#4a6070;letter-spacing:0.14em;text-transform:uppercase;margin-bottom:0.35rem;\">{_E(label)}</div>"
            f"<div class=\"anim-count\" style=\"font-family:'JetBrains Mono',monospace;"
            f"font-size:1.6rem;font-weight:700;color:{color};line-height:1;\">{_E(str(value))}</div>"
            f"{sub_html}</div>"
        )

    # ── shared data source ────────────────────────────────────────
    dash_df    = st.session_state.clean_df.copy() if st.session_state.clean_df is not None else df_raw.copy()
    dash_label = "✅ Cleaned" if st.session_state.clean_df is not None else "⚠️ Raw (not yet cleaned)"

    num_cols      = dash_df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols      = dash_df.select_dtypes(include=["object", "category"]).columns.tolist()
    all_dash_cols = dash_df.columns.tolist()

    # ── plotly theme ──────────────────────────────────────────────
    _DLL = dict(
        template="plotly_dark",
        paper_bgcolor="#060809",
        plot_bgcolor="#0c1014",
        font=dict(family="JetBrains Mono, monospace", color="#dce8f0", size=11),
    )
    _DL = dict(template="plotly_dark")

    # ── Header ────────────────────────────────────────────────────
    st.markdown(
        "<div class=\"anim-up\" style=\"font-family:Syne,'Syne',sans-serif;font-size:1.8rem;"
        "font-weight:800;color:#dce8f0;letter-spacing:-0.02em;margin-bottom:0.2rem;\">Dashboard</div>"
        "<div style=\"width:60px;height:2px;background:#00e5a0;margin-bottom:0.7rem;\"></div>",
        unsafe_allow_html=True
    )

    hdr_l, hdr_r = st.columns([3, 1])
    with hdr_l:
        st.markdown(
            f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.7rem;"
            f"color:#4a6070;\">Source: <span style=\"color:#dce8f0;\">{dash_label}</span>"
            f" &nbsp;·&nbsp; {len(dash_df):,} rows &nbsp;·&nbsp; {len(dash_df.columns)} cols</div>",
            unsafe_allow_html=True
        )
    with hdr_r:
        accent_color = st.color_picker("Accent", "#00e5a0", key="dash_accent")

    color_seq = [accent_color, "#00b87a", "#ffb347", "#7eb8f7", "#c084fc", "#ff4444"]

    # ── AI Insights Banner (if strategy loaded) ────────────────────
    _ai_strat = st.session_state.get("ai_strategy")
    if _ai_strat and not _ai_strat.get("error"):
        _ai_conf  = _ai_strat.get("confidence", "MEDIUM")
        _ai_exec  = _ai_strat.get("executive_summary", "")
        _ai_risks = _ai_strat.get("risk_flags", [])
        _conf_c   = {"HIGH": "#00e5a0", "MEDIUM": "#ffb347", "LOW": "#ff4444"}.get(_ai_conf, "#4a6070")
        _conf_bg  = {"HIGH": "#061a10", "MEDIUM": "#1a1008", "LOW": "#1a0808"}.get(_ai_conf, "#0c1014")
        _risk_html = "".join(
            f"<span style=\"background:#1a1008;border:1px solid #ffb34733;border-radius:4px;"
            f"padding:2px 8px;font-size:0.62rem;color:#ffb347;white-space:nowrap;\">&#9873; {_E(r)}</span> "
            for r in _ai_risks[:4]
        )
        st.markdown(
            f"<div class=\"anim-up\" style=\"background:{_conf_bg};border:1px solid {_conf_c}33;"
            f"border-left:4px solid {_conf_c};border-radius:8px;"
            f"padding:1rem 1.3rem;margin-bottom:0.8rem;\">"
            f"<div style=\"display:flex;align-items:center;gap:0.6rem;margin-bottom:0.5rem;\">"
            f"<span style=\"font-size:1.1rem;\">&#129302;</span>"
            f"<span class=\"card-title\" style=\"font-family:Syne,'Syne',sans-serif;font-size:0.9rem;"
            f"font-weight:800;color:#dce8f0;\">AI Assessment Active</span>"
            f"<span style=\"margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:0.52rem;"
            f"color:{_conf_c};border:1px solid {_conf_c}44;padding:2px 8px;border-radius:20px;"
            f"\">{_ai_conf} CONFIDENCE</span></div>"
            f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.7rem;"
            f"color:#c0d0d8;line-height:1.7;margin-bottom:0.5rem;\">{_E(_ai_exec)}</div>"
            f"<div style=\"display:flex;flex-wrap:wrap;gap:0.3rem;\">{_risk_html}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style=\"background:#0c1014;border:1px solid #1c2a35;border-radius:8px;"
            "padding:0.8rem 1.2rem;margin-bottom:0.8rem;display:flex;align-items:center;gap:0.8rem;\">"
            "<span style=\"font-size:1.1rem;\">&#129302;</span>"
            "<span style=\"font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#4a6070;\">"
            "No AI strategy loaded. Go to <b style=\"color:#dce8f0;\">Smart Clean → AI Advisor</b> "
            "and click Generate AI Strategy for AI-powered insights here.</span></div>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════
    # INNER TABS
    # ══════════════════════════════════════════════════════════════
    (d_tab1, d_tab2, d_tab3, d_tab4,
     d_tab5, d_tab6, d_tab7, d_tab8,
     d_tab9, d_tab10) = st.tabs([
        "🔍 Explorer",
        "📊 Distribution",
        "🔗 Correlation",
        "📦 Outliers",
        "🚫 Missing",
        "🏷️ Top Values",
        "🔬 Profiler",
        "🏥 Quality",
        "🤖 AI Insights",
        "📥 Export",
    ])

    # ══════════════════════════════════════════════════════════════
    # D-TAB 1 — EXPLORER (custom chart builder + aggregation)
    # ══════════════════════════════════════════════════════════════
    with d_tab1:
        st.markdown(_sec("🔍", "Chart Explorer"), unsafe_allow_html=True)

        CHART_HINTS = {
            "Histogram": "Shows how a number is spread. Pick a numeric X. No Y needed.",
            "Bar":       "Compare values across categories. Choose aggregation below.",
            "Line":      "Shows trend over ordered data. X = date/order, Y = number.",
            "Scatter":   "Reveals relationships between two numbers. Color by category.",
            "Box":       "Shows median, spread and outliers. Color to compare groups.",
            "Violin":    "Like Box but also shows distribution shape.",
            "Area":      "Like Line but filled. Good for showing volume over time.",
        }

        # ── Row 1: chart type + X + Y + color ────────────────────
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        with r1c1:
            chart_type = st.selectbox("① Chart type", list(CHART_HINTS), key="exp_type")
            st.markdown(
                f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.62rem;"
                f"color:#3a6050;line-height:1.4;margin-top:-0.2rem;\">{CHART_HINTS[chart_type]}</div>",
                unsafe_allow_html=True
            )
        with r1c2:
            x_col = st.selectbox("② X axis", all_dash_cols, key="exp_x")
        with r1c3:
            y_label = "③ Y axis" if chart_type not in ("Histogram",) else "③ Y axis (auto)"
            y_col_raw = st.selectbox(y_label, ["(none)"] + num_cols, key="exp_y")
            y_col = None if y_col_raw == "(none)" else y_col_raw
        with r1c4:
            color_col_raw = st.selectbox("④ Group / Color", ["(none)"] + cat_cols, key="exp_color")
            color_col = None if color_col_raw == "(none)" else color_col_raw

        # ── Row 2: aggregation + filter ───────────────────────────
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1:
            AGG_OPTIONS = ["Count", "Sum", "Average", "Median", "Min", "Max"]
            agg_choice  = st.selectbox("⑤ Aggregation (for Bar)", AGG_OPTIONS, key="exp_agg",
                                       help="How to reduce multiple rows per X value.\nCount = number of rows, Sum = total, Average = mean.")
            agg_map = {"Count": "count", "Sum": "sum", "Average": "mean",
                       "Median": "median", "Min": "min", "Max": "max"}
            agg_fn = agg_map[agg_choice]
        with r2c2:
            fcol = st.selectbox("⑥ Filter column", ["(none)"] + all_dash_cols, key="exp_fcol")
        with r2c3:
            fop_labels = {"==": "= equals", "!=": "≠ not equal", ">": "> greater",
                          "<": "< less", ">=": "≥ at least", "<=": "≤ at most",
                          "contains": "contains text"}
            fop_choice = st.selectbox("Condition", list(fop_labels.values()), key="exp_fop")
            fop = [k for k, v in fop_labels.items() if v == fop_choice][0]
        with r2c4:
            fval = st.text_input("Filter value", "", key="exp_fval", placeholder="e.g. Egypt or 1000")

        # ── Advanced ──────────────────────────────────────────────
        with st.expander("⚙️ Advanced options", expanded=False):
            ac1, ac2, ac3 = st.columns(3)
            with ac1:
                nbins = st.slider("Histogram bins", 5, 100, 30, key="exp_bins")
            with ac2:
                _max_r = max(100, len(dash_df))
                max_rows = st.slider("Max rows to plot", 100, _max_r, min(5000, len(dash_df)), 100,
                                     key="exp_rows") if len(dash_df) > 100 else len(dash_df)
            with ac3:
                top_n = st.slider("Top N (Bar/count)", 5, 50, 15, key="exp_topn")

        # ── Apply filter ──────────────────────────────────────────
        plot_df = dash_df.head(max_rows).copy()
        if fcol != "(none)" and fval.strip():
            try:
                s = plot_df[fcol]
                v = fval.strip()
                if fop == "==":          plot_df = plot_df[s.astype(str) == v]
                elif fop == "!=":        plot_df = plot_df[s.astype(str) != v]
                elif fop == "contains":  plot_df = plot_df[s.astype(str).str.contains(v, case=False, na=False)]
                else:
                    nv = float(v)
                    # FIX: convert to numeric first to avoid category dtype crash
                    s_num = pd.to_numeric(s, errors="coerce")
                    ops = {">": s_num.__gt__, "<": s_num.__lt__, ">=": s_num.__ge__, "<=": s_num.__le__}
                    plot_df = plot_df[ops[fop](nv)]
                st.markdown(
                    f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.7rem;"
                    f"color:{accent_color};\">▸ Filter: {len(plot_df):,} of {len(dash_df):,} rows</div>",
                    unsafe_allow_html=True
                )
            except Exception as fe:
                st.warning(f"Filter error: {fe}")

        # ── Build chart (FIXED logic) ──────────────────────────────
        try:
            fig = None
            if chart_type == "Histogram":
                if x_col in num_cols or pd.api.types.is_numeric_dtype(plot_df[x_col]):
                    fig = px.histogram(plot_df, x=x_col, nbins=nbins, color=color_col,
                                       color_discrete_sequence=color_seq,
                                       title=f"Distribution of '{x_col}'", **_DL)
                else:
                    vc = plot_df[x_col].value_counts().head(top_n)
                    fig = px.bar(x=vc.index, y=vc.values, labels={"x": x_col, "y": "Count"},
                                 color_discrete_sequence=color_seq,
                                 title=f"Value counts — '{x_col}'", **_DL)

            elif chart_type == "Bar":
                if y_col:
                    # FIX: aggregate properly instead of plotting raw rows
                    if agg_fn == "count":
                        agg_df = plot_df.groupby(x_col, observed=True)[y_col].count().reset_index()
                        y_title = f"Count of {y_col}"
                    else:
                        agg_df = plot_df.groupby(x_col, observed=True)[y_col].agg(agg_fn).reset_index()
                        y_title = f"{agg_choice} of {y_col}"
                    agg_df = agg_df.nlargest(top_n, y_col)
                    fig = px.bar(agg_df, x=x_col, y=y_col,
                                 color=x_col if color_col is None else color_col,
                                 color_discrete_sequence=color_seq,
                                 title=f"{y_title} by '{x_col}'", **_DL)
                    fig.update_layout(showlegend=False)
                else:
                    vc = plot_df[x_col].value_counts().head(top_n)
                    fig = px.bar(x=vc.index, y=vc.values, labels={"x": x_col, "y": "Count"},
                                 color=vc.values,
                                 color_continuous_scale=[[0, "#0c1014"], [1, accent_color]],
                                 title=f"Top {top_n} — '{x_col}'", **_DL)
                    fig.update_layout(coloraxis_showscale=False)

            elif chart_type == "Line":
                if y_col:
                    fig = px.line(plot_df, x=x_col, y=y_col, color=color_col,
                                  color_discrete_sequence=color_seq,
                                  title=f"'{y_col}' over '{x_col}'", **_DL)
                else:
                    st.info("Select a numeric Y axis for the Line chart.")

            elif chart_type == "Scatter":
                if y_col:
                    fig = px.scatter(plot_df, x=x_col, y=y_col, color=color_col,
                                     color_discrete_sequence=color_seq, opacity=0.65,
                                     title=f"'{x_col}' vs '{y_col}'", **_DL)
                else:
                    st.info("Select a numeric Y axis for the Scatter chart.")

            elif chart_type == "Box":
                # FIX: use y_col if provided, otherwise auto-pick numeric
                y_box = y_col if y_col else (x_col if x_col in num_cols else (num_cols[0] if num_cols else x_col))
                x_box = color_col if color_col else (x_col if x_col in cat_cols else None)
                fig = px.box(plot_df, x=x_box, y=y_box, color=color_col,
                             color_discrete_sequence=color_seq,
                             title=f"Spread — '{y_box}'" + (f" by '{x_box}'" if x_box else ""), **_DL)

            elif chart_type == "Violin":
                y_vio = y_col if y_col else (x_col if x_col in num_cols else (num_cols[0] if num_cols else x_col))
                x_vio = color_col if color_col else (x_col if x_col in cat_cols else None)
                fig = px.violin(plot_df, x=x_vio, y=y_vio, color=color_col,
                                color_discrete_sequence=color_seq, box=True,
                                title=f"Distribution shape — '{y_vio}'", **_DL)

            elif chart_type == "Area":
                if y_col:
                    fig = px.area(plot_df, x=x_col, y=y_col, color=color_col,
                                  color_discrete_sequence=color_seq,
                                  title=f"'{y_col}' over '{x_col}'", **_DL)
                else:
                    st.info("Select a numeric Y axis for the Area chart.")

            if fig:
                fig.update_layout(height=460, margin=dict(t=50, b=20, l=20, r=20), **_DLL)
                fig.update_traces(marker_line_width=0)
                st.plotly_chart(fig, use_container_width=True)

        except Exception as ce:
            st.error(f"Chart error: {ce}")

        st.markdown("---")
        prev_n = st.slider("Preview rows", 5, 200, 30, key="exp_prev")
        st.dataframe(plot_df.head(prev_n), use_container_width=True, height=280)
        st.download_button("⬇ Download filtered data (CSV)",
                           plot_df.to_csv(index=False).encode(),
                           "filtered_data.csv", "text/csv", key="dl_filtered")

    # ══════════════════════════════════════════════════════════════
    # D-TAB 2 — DISTRIBUTION
    # ══════════════════════════════════════════════════════════════
    with d_tab2:
        st.markdown(_sec("📊", "Distribution Explorer"), unsafe_allow_html=True)
        if not num_cols:
            st.info("No numeric columns found.")
        else:
            d1, d2, d3 = st.columns(3)
            with d1: dist_col  = st.selectbox("Column", num_cols, key="dist_col2")
            with d2: dist_bins = st.slider("Bins", 5, 100, 30, key="dist_bins2")
            with d3:
                dist_marg = st.selectbox("Marginal plot", ["none", "box", "violin", "rug"], key="dist_marg")
                dist_marg = None if dist_marg == "none" else dist_marg
            grp_col = st.selectbox("Split by (optional)", ["(none)"] + cat_cols, key="dist_grp")
            grp_col = None if grp_col == "(none)" else grp_col

            fig_dist = px.histogram(dash_df, x=dist_col, nbins=dist_bins, color=grp_col,
                                    color_discrete_sequence=color_seq, marginal=dist_marg,
                                    title=f"Distribution — {dist_col}", **_DL)
            fig_dist.update_layout(height=420, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
            st.plotly_chart(fig_dist, use_container_width=True)

            s = dash_df[dist_col].dropna()
            sc1, sc2, sc3, sc4, sc5 = st.columns(5)
            sc1.metric("Mean",   f"{s.mean():.3g}")
            sc2.metric("Median", f"{s.median():.3g}")
            sc3.metric("Std",    f"{s.std():.3g}")
            sc4.metric("Skew",   f"{float(s.skew()):.3f}")
            sc5.metric("Nulls",  int(dash_df[dist_col].isnull().sum()))

    # ══════════════════════════════════════════════════════════════
    # D-TAB 3 — CORRELATION
    # ══════════════════════════════════════════════════════════════
    with d_tab3:
        st.markdown(_sec("🔗", "Correlation Heatmap"), unsafe_allow_html=True)
        if len(num_cols) < 2:
            st.info("Need ≥ 2 numeric columns.")
        else:
            sel_corr   = st.multiselect("Columns", num_cols, default=num_cols[:min(10, len(num_cols))], key="corr_sel")
            corr_meth  = st.radio("Method", ["pearson", "spearman", "kendall"], horizontal=True, key="corr_method")
            if len(sel_corr) >= 2:
                corr_mx = dash_df[sel_corr].corr(method=corr_meth)
                fig_corr = px.imshow(corr_mx, text_auto=".2f",
                                     color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                                     title=f"Correlation Matrix ({corr_meth})", **_DL)
                fig_corr.update_layout(height=480, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
                st.plotly_chart(fig_corr, use_container_width=True)

                mask  = np.triu(np.ones(corr_mx.shape), k=1).astype(bool)
                pairs = (corr_mx.where(mask).stack()
                         .reset_index().rename(columns={"level_0":"Col A","level_1":"Col B",0:"r"})
                         .assign(abs_r=lambda d: d["r"].abs())
                         .sort_values("abs_r", ascending=False).drop(columns="abs_r").reset_index(drop=True))
                st.markdown(_sec("", "Top correlated pairs"), unsafe_allow_html=True)
                st.dataframe(pairs.head(10), use_container_width=True, height=280)
            else:
                st.info("Select at least 2 columns.")

    # ══════════════════════════════════════════════════════════════
    # D-TAB 4 — OUTLIERS
    # ══════════════════════════════════════════════════════════════
    with d_tab4:
        st.markdown(_sec("📦", "Outlier Analysis"), unsafe_allow_html=True)
        if not num_cols:
            st.info("No numeric columns.")
        else:
            o1, o2 = st.columns(2)
            with o1: out_cols = st.multiselect("Columns", num_cols, default=num_cols[:min(4,len(num_cols))], key="out_cols")
            with o2: out_type = st.radio("Plot type", ["Box","Violin"], horizontal=True, key="out_type")
            if out_cols:
                fig_out = go.Figure()
                for i, col in enumerate(out_cols):
                    c = color_seq[i % len(color_seq)]
                    if out_type == "Box":
                        fig_out.add_trace(go.Box(y=dash_df[col], name=col, marker_color=c,
                                                  boxmean="sd", line_width=1.5))
                    else:
                        fig_out.add_trace(go.Violin(y=dash_df[col], name=col,
                                                     line_color=c, fillcolor=c+"33",
                                                     box_visible=True, meanline_visible=True))
                fig_out.update_layout(height=420, margin=dict(t=20,b=20,l=20,r=20),
                                      showlegend=True, **_DLL)
                st.plotly_chart(fig_out, use_container_width=True)

                rows = []
                for col in out_cols:
                    s = dash_df[col].dropna().astype(float)
                    if s.empty: continue
                    q1, q3 = s.quantile(.25), s.quantile(.75)
                    iqr = q3 - q1
                    n_out = int(((s < q1-1.5*iqr) | (s > q3+1.5*iqr)).sum())
                    rows.append({"Column": col, "Min": round(s.min(),3), "Max": round(s.max(),3),
                                 "Mean": round(s.mean(),3), "Std": round(s.std(),3),
                                 "IQR": round(iqr,3), "Outliers (IQR)": n_out})
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.info("Select at least one column.")

    # ══════════════════════════════════════════════════════════════
    # D-TAB 5 — MISSING VALUES
    # ══════════════════════════════════════════════════════════════
    with d_tab5:
        st.markdown(_sec("🚫", "Missing Values Map"), unsafe_allow_html=True)
        null_df = pd.DataFrame({
            "Column":    dash_df.columns,
            "Missing":   dash_df.isnull().sum().values,
            "Missing %": (dash_df.isnull().mean()*100).round(2).values,
            "Present":   dash_df.notnull().sum().values,
        }).sort_values("Missing %", ascending=False)
        has_nulls = null_df[null_df["Missing"] > 0]

        if has_nulls.empty:
            st.success("🎉 Zero missing values in this dataset!")
        else:
            m1, m2 = st.columns(2)
            with m1:
                fig_nh = px.bar(has_nulls, x="Missing %", y="Column", orientation="h",
                                color="Missing %",
                                color_continuous_scale=[[0,"#1c2a35"],[0.5,"#ffb347"],[1,"#ff4444"]],
                                title="Missing % per Column", **_DL)
                fig_nh.update_layout(height=380, margin=dict(t=40,b=10,l=10,r=10),
                                     coloraxis_showscale=False, **_DLL)
                st.plotly_chart(fig_nh, use_container_width=True)
            with m2:
                fig_stk = go.Figure()
                fig_stk.add_trace(go.Bar(name="Present", y=null_df["Column"],
                                          x=null_df["Present"], orientation="h",
                                          marker_color=accent_color, opacity=0.8))
                fig_stk.add_trace(go.Bar(name="Missing", y=null_df["Column"],
                                          x=null_df["Missing"], orientation="h",
                                          marker_color="#ff4444", opacity=0.8))
                fig_stk.update_layout(barmode="stack", height=380, title="Present vs Missing",
                                      margin=dict(t=40,b=10,l=10,r=10), **_DLL)
                st.plotly_chart(fig_stk, use_container_width=True)
            st.dataframe(null_df, use_container_width=True, height=220)

    # ══════════════════════════════════════════════════════════════
    # D-TAB 6 — TOP VALUES (with aggregation)
    # ══════════════════════════════════════════════════════════════
    with d_tab6:
        st.markdown(_sec("🏷️", "Top Values"), unsafe_allow_html=True)
        if not cat_cols:
            st.info("No categorical columns found.")
        else:
            tv_r1c1, tv_r1c2, tv_r1c3 = st.columns(3)
            with tv_r1c1: tv_col = st.selectbox("Category column", cat_cols, key="tv_col2")
            with tv_r1c2: tv_n   = st.slider("Top N", 3, 50, 15, key="tv_n2")
            with tv_r1c3:
                tv_agg_choice = st.selectbox("Aggregation", ["Count", "Sum", "Average", "Median"], key="tv_agg")
                tv_agg_map = {"Count": "count", "Sum": "sum", "Average": "mean", "Median": "median"}
                tv_agg = tv_agg_map[tv_agg_choice]

            tv_val_col = None
            if tv_agg != "count" and num_cols:
                tv_val_col = st.selectbox("Numeric column to aggregate", num_cols, key="tv_val")

            grp_tv = st.selectbox("Compare by (optional)", ["(none)"] + [c for c in cat_cols if c != tv_col], key="tv_grp")
            grp_tv = None if grp_tv == "(none)" else grp_tv

            if tv_agg == "count" or tv_val_col is None:
                if grp_tv:
                    grp_data = dash_df.groupby([tv_col, grp_tv], observed=True).size().reset_index(name="count")
                    top_vals = dash_df[tv_col].value_counts().head(tv_n).index
                    grp_data = grp_data[grp_data[tv_col].isin(top_vals)]
                    fig_tv = px.bar(grp_data, x=tv_col, y="count", color=grp_tv,
                                    color_discrete_sequence=color_seq, barmode="stack",
                                    title=f"Count of '{tv_col}' by '{grp_tv}'", **_DL)
                else:
                    top = dash_df[tv_col].value_counts().head(tv_n)
                    fig_tv = px.bar(x=top.index, y=top.values,
                                    labels={"x": tv_col, "y": "Count"},
                                    color=top.values,
                                    color_continuous_scale=[[0, "#0c1014"], [1, accent_color]],
                                    title=f"Top {tv_n} — '{tv_col}'", **_DL)
                    fig_tv.update_layout(coloraxis_showscale=False)
            else:
                agg_tv = dash_df.groupby(tv_col, observed=True)[tv_val_col].agg(tv_agg).nlargest(tv_n).reset_index()
                fig_tv = px.bar(agg_tv, x=tv_col, y=tv_val_col,
                                color=tv_col, color_discrete_sequence=color_seq,
                                title=f"{tv_agg_choice} of '{tv_val_col}' by '{tv_col}'", **_DL)
                fig_tv.update_layout(showlegend=False)

            fig_tv.update_layout(height=420, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
            st.plotly_chart(fig_tv, use_container_width=True)

            # Pie chart
            top_pie = dash_df[tv_col].value_counts().head(tv_n)
            fig_pie = px.pie(values=top_pie.values, names=top_pie.index,
                             color_discrete_sequence=color_seq,
                             title=f"Share — '{tv_col}'", **_DL)
            fig_pie.update_layout(height=350, margin=dict(t=50,b=20,l=20,r=20), **_DLL)
            st.plotly_chart(fig_pie, use_container_width=True)

    # ══════════════════════════════════════════════════════════════
    # D-TAB 7 — COLUMN PROFILER
    # ══════════════════════════════════════════════════════════════
    with d_tab7:
        st.markdown(_sec("🔬", "Column Profiler"), unsafe_allow_html=True)
        prof_col   = st.selectbox("Select column", dash_df.columns.tolist(), key="prof_col")
        col_series = dash_df[prof_col]
        total      = len(col_series)
        nulls      = int(col_series.isnull().sum())
        null_pct   = round(nulls / total * 100, 1) if total > 0 else 0.0
        unique     = int(col_series.nunique())
        dtype      = str(col_series.dtype)
        is_num     = pd.api.types.is_numeric_dtype(col_series)
        s_clean    = col_series.dropna()

        p1,p2,p3,p4,p5 = st.columns(5)
        p1.metric("Rows",        f"{total:,}")
        p2.metric("Nulls",       f"{nulls:,}", delta=f"{null_pct}%", delta_color="inverse" if null_pct > 0 else "off")
        p3.metric("Unique",      f"{unique:,}")
        p4.metric("Dtype",       dtype)
        p5.metric("Fill rate",   f"{100-null_pct:.1f}%", delta_color="normal" if null_pct < 20 else "inverse")

        pc_l, pc_r = st.columns(2)
        with pc_l:
            st.markdown(_sec("", "Stats"), unsafe_allow_html=True)
            if is_num and len(s_clean) > 0:
                q1v, q3v = float(s_clean.quantile(0.25)), float(s_clean.quantile(0.75))
                st.dataframe(pd.DataFrame({
                    "Metric": ["Min","Max","Mean","Median","Std dev","Skewness","Kurtosis","Q1 (25%)","Q3 (75%)","IQR"],
                    "Value":  [f"{s_clean.min():.4g}", f"{s_clean.max():.4g}",
                               f"{s_clean.mean():.4g}", f"{s_clean.median():.4g}",
                               f"{s_clean.std():.4g}", f"{float(s_clean.skew()):.3f}",
                               f"{float(s_clean.kurtosis()):.3f}",
                               f"{q1v:.4g}", f"{q3v:.4g}", f"{q3v-q1v:.4g}"]
                }), use_container_width=True, hide_index=True, height=380)
            else:
                top10 = col_series.value_counts().head(10)
                st.dataframe(pd.DataFrame({"Value": top10.index.astype(str),
                                           "Count": top10.values,
                                           "Share %": (top10.values/total*100).round(1)}),
                             use_container_width=True, hide_index=True, height=380)
        with pc_r:
            st.markdown(_sec("", "Distribution"), unsafe_allow_html=True)
            if is_num and len(s_clean) > 1:
                fp = px.histogram(s_clean, nbins=30, color_discrete_sequence=[accent_color],
                                  title=f"{prof_col} distribution", **_DL)
                fp.update_layout(height=380, margin=dict(t=40,b=20,l=20,r=20),
                                 showlegend=False, **_DLL)
                fp.update_traces(marker_line_width=0)
                st.plotly_chart(fp, use_container_width=True)
            elif len(s_clean) > 0:
                tnp = col_series.value_counts().head(20)
                fp = px.bar(x=tnp.index.astype(str), y=tnp.values,
                            color_continuous_scale=[[0,"#0c1014"],[1,accent_color]],
                            color=tnp.values, labels={"x": prof_col, "y": "Count"},
                            title=f"Top 20 — {prof_col}", **_DL)
                fp.update_layout(height=380, margin=dict(t=40,b=20,l=20,r=20),
                                 coloraxis_showscale=False, **_DLL)
                st.plotly_chart(fp, use_container_width=True)

        # Sample values
        st.markdown(_sec("", "Sample Values"), unsafe_allow_html=True)
        sample_vals = s_clean.sample(min(8, len(s_clean)), random_state=42) if len(s_clean) >= 1 else s_clean
        st.markdown(
            " &nbsp; ".join(
                f"<code style=\"background:#111820;border:1px solid #1c2a35;"
                f"padding:2px 8px;border-radius:4px;font-size:0.75rem;"
                f"color:#dce8f0;\">{_E(str(v)[:40])}</code>"
                for v in sample_vals.tolist()
            ),
            unsafe_allow_html=True
        )

    # ══════════════════════════════════════════════════════════════
    # D-TAB 8 — QUALITY
    # ══════════════════════════════════════════════════════════════
    with d_tab8:
        st.markdown(_sec("🏥", "Data Quality"), unsafe_allow_html=True)
        score_before = report["health_score"]
        grade_before = report["health_grade"]
        grade_color  = {"A":"#00e5a0","B":"#7eb8f7","C":"#ffb347","D":"#ff4444"}.get(grade_before,"#dce8f0")
        sev_counts   = {"HIGH":0,"MEDIUM":0,"OK":0}
        for v in checks.values():
            sev_counts[v.get("severity","OK")] = sev_counts.get(v.get("severity","OK"),0) + 1

        # KPI row
        qk_html = "".join([
            _kpi_card("HIGH severity",   sev_counts["HIGH"],   "#ff4444"),
            _kpi_card("MEDIUM severity", sev_counts["MEDIUM"], "#ffb347"),
            _kpi_card("Passed checks",   sev_counts["OK"],     "#00e5a0"),
            _kpi_card("Health score",    f"{score_before}%  Grade {grade_before}", grade_color),
        ])
        st.markdown(
            f"<div style=\"display:grid;grid-template-columns:repeat(4,1fr);gap:0.75rem;"
            f"margin-bottom:1rem;\">{qk_html}</div>",
            unsafe_allow_html=True
        )

        fig_sev = px.bar(x=["HIGH","MEDIUM","OK"],
                         y=[sev_counts["HIGH"],sev_counts["MEDIUM"],sev_counts["OK"]],
                         color=["HIGH","MEDIUM","OK"],
                         color_discrete_map={"HIGH":"#ff4444","MEDIUM":"#ffb347","OK":accent_color},
                         labels={"x":"Severity","y":"Checks"}, title="Audit Checks by Severity", **_DL)
        fig_sev.update_layout(height=260, showlegend=False, margin=dict(t=40,b=20,l=20,r=20), **_DLL)
        st.plotly_chart(fig_sev, use_container_width=True)

        issues_rows = [{"Check": v["label"], "Severity": v.get("severity","OK"),
                        "Found": "✅" if v.get("found") else "—",
                        "Category": {"A":"Auto-fix","M":"Manual"}.get(v.get("category",""),""),
                        "Suggestion": (v.get("suggestion","") or "")[:70]}
                       for v in checks.values()]
        if issues_rows:
            def _col_sev(val):
                return {"HIGH":"color:#ff4444","MEDIUM":"color:#ffb347","OK":"color:#00e5a0"}.get(val,"")
            st.dataframe(pd.DataFrame(issues_rows).style.map(_col_sev, subset=["Severity"]),
                         use_container_width=True, height=min(40+len(issues_rows)*35,500), hide_index=True)

        st.markdown("---")
        if st.session_state.get("clean_summary"):
            cs          = st.session_state.clean_summary
            score_after = cs.get("health_after", score_before)
            grade_after = "A" if score_after>=90 else "B" if score_after>=75 else "C" if score_after>=55 else "D"
            ga_color    = {"A":accent_color,"B":"#7eb8f7","C":"#ffb347","D":"#ff4444"}.get(grade_after,"#dce8f0")
            delta       = score_after - score_before
            st.markdown(_sec("", "Before vs After Cleaning"), unsafe_allow_html=True)
            st.markdown(
                f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#4a6070;"
                f"margin-bottom:0.5rem;\">Score: "
                f"<span style=\"color:#ff4444;\">{score_before}%</span> → "
                f"<span style=\"color:{ga_color};\">{score_after}%</span> "
                f"<span style=\"color:{'#00e5a0' if delta>=0 else '#ff4444'};\">"
                f"({delta:+} pts)</span></div>",
                unsafe_allow_html=True
            )
            st.progress(min(score_after/100.0, 1.0))
            q1, q2 = st.columns(2)
            def _gauge(val, title, color):
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number", value=val,
                    title={"text": title, "font": {"size": 12, "color": "#4a6070", "family": "JetBrains Mono"}},
                    number={"suffix": "%", "font": {"size": 38, "color": color, "family": "JetBrains Mono"}},
                    gauge={"axis": {"range": [0,100], "tickcolor": "#1c2a35"},
                           "bar":  {"color": color, "thickness": 0.5},
                           "bgcolor": "#0c1014", "bordercolor": "#1c2a35",
                           "steps": [{"range":[0,55],"color":"#1a0808"},
                                     {"range":[55,75],"color":"#1a1008"},
                                     {"range":[75,100],"color":"#061a10"}]}))
                fig_g.update_layout(height=260, margin=dict(t=50,b=10,l=20,r=20), **_DLL)
                return fig_g
            with q1: st.plotly_chart(_gauge(score_before, f"Before · Grade {grade_before}", "#ff4444"), use_container_width=True)
            with q2: st.plotly_chart(_gauge(score_after,  f"After  · Grade {grade_after}",  ga_color),  use_container_width=True)
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Score Δ",      f"{delta:+} pts", delta_color="normal")
            m2.metric("Rows removed", abs(cs["rows_removed"]), delta_color="inverse")
            m3.metric("Cols removed", abs(cs["cols_removed"]), delta_color="inverse")
            m4.metric("Nulls fixed",  cs["nulls_fixed"],       delta_color="normal")
        else:
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number", value=score_before,
                title={"text": f"Health Score · Grade {grade_before}",
                       "font": {"family":"JetBrains Mono","size":13,"color":"#4a6070"}},
                number={"suffix":"%","font":{"size":48,"color":grade_color,"family":"JetBrains Mono"}},
                gauge={"axis":{"range":[0,100],"tickcolor":"#1c2a35"},
                       "bar":{"color":grade_color,"thickness":0.5},
                       "bgcolor":"#0c1014","bordercolor":"#1c2a35",
                       "threshold":{"line":{"color":"#dce8f0","width":2},"thickness":0.75,"value":75},
                       "steps":[{"range":[0,55],"color":"#1a0808"},
                                {"range":[55,75],"color":"#1a1008"},
                                {"range":[75,90],"color":"#0a1408"},
                                {"range":[90,100],"color":"#061a10"}]}))
            fig_g.update_layout(height=350, margin=dict(t=60,b=20,l=30,r=30), **_DLL)
            st.plotly_chart(fig_g, use_container_width=True)
            st.info("→ Run Smart Clean (Tab 3) to unlock the Before vs After comparison.")

    # ══════════════════════════════════════════════════════════════
    # D-TAB 9 — AI INSIGHTS IN DASHBOARD CONTEXT
    # ══════════════════════════════════════════════════════════════
    with d_tab9:
        import json as _json
        import urllib.request as _ureq
        import urllib.error   as _uerr
        import re as _re

        st.markdown(_sec("🤖", "AI Chart Intelligence"), unsafe_allow_html=True)

        # ── helpers ───────────────────────────────────────────────
        _GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={key}"
        _MODELS     = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-001", "gemini-1.0-pro"]

        def _gemini_call(prompt: str, api_key: str) -> str:
            """Fire prompt at Gemini, return raw text, try models in order."""
            for model in _MODELS:
                try:
                    url  = _GEMINI_URL.format(model=model, key=api_key)
                    body = _json.dumps({
                        "contents":         [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.25, "maxOutputTokens": 4096},
                    }).encode()
                    req  = _ureq.Request(url, data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
                    with _ureq.urlopen(req, timeout=45) as r:
                        return _json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
                except _uerr.HTTPError as e:
                    body_txt = ""
                    try: body_txt = e.read().decode()
                    except: pass
                    if e.code in (400, 403) and "api key" in body_txt.lower():
                        raise RuntimeError("Invalid API key — get one free at aistudio.google.com")
                    continue
                except Exception:
                    continue
            raise RuntimeError("All Gemini models failed. Check your key and network.")

        def _parse_charts_json(raw: str) -> list:
            """Extract JSON array from Gemini response."""
            text  = raw.strip()
            text  = _re.sub(r"^```(?:json)?\s*\n?", "", text)
            text  = _re.sub(r"\n?\s*```\s*$",       "", text)
            start = text.find("[")
            end   = text.rfind("]") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON array in response")
            return _json.loads(text[start:end])

        def _build_profile(df: pd.DataFrame) -> dict:
            """Compact dataset profile to send to AI — saves tokens."""
            num_c = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_c = df.select_dtypes(include=["object","category"]).columns.tolist()
            profile = {
                "shape":        {"rows": len(df), "cols": len(df.columns)},
                "numeric_cols": num_c[:20],
                "cat_cols":     cat_c[:20],
                "null_pct":     {c: round(float(df[c].isnull().mean()*100), 1) for c in df.columns[:30]},
                "cat_cardinality": {c: int(df[c].nunique()) for c in cat_c[:15]},
                "num_stats": {
                    c: {
                        "min":    round(float(df[c].dropna().min()), 4) if len(df[c].dropna()) else None,
                        "max":    round(float(df[c].dropna().max()), 4) if len(df[c].dropna()) else None,
                        "mean":   round(float(df[c].dropna().mean()), 4) if len(df[c].dropna()) else None,
                        "skew":   round(float(df[c].dropna().skew()), 3) if len(df[c].dropna()) > 2 else None,
                        "nullpct":round(float(df[c].isnull().mean()*100), 1),
                    }
                    for c in num_c[:15]
                },
                "sample_values": {c: df[c].dropna().sample(min(5, df[c].dropna().shape[0]),
                                     random_state=1).astype(str).tolist()
                                  for c in cat_c[:8] if df[c].dropna().shape[0] > 0},
            }
            return profile

        _CHART_PROMPT_TEMPLATE = """You are a world-class data analyst with 20+ years of experience.
You have been given a structured profile of a dataset. Your job is to recommend the 6 MOST INSIGHTFUL charts that will reveal the most valuable patterns, anomalies, correlations, and business intelligence hidden in this data.

DATASET PROFILE:
{profile}

RULES:
- Only use columns that actually exist in the profile above.
- Numeric columns for bar/line/scatter/box/histogram Y axes.
- Categorical columns for bar X axes, pie names, color grouping.
- chart_type must be one of: bar | line | scatter | histogram | box | violin | pie | heatmap_corr
- For heatmap_corr: set x_col and y_col to the two most correlated numeric columns.
- For pie: x_col = the categorical column, y_col = null.
- For histogram: x_col = a numeric column, y_col = null.
- For bar: x_col = category, y_col = numeric, agg = one of count|sum|mean|median|min|max.
- For scatter: x_col and y_col must both be numeric.
- For box/violin: y_col = numeric, x_col = a low-cardinality categorical column (or null).
- color_col: optional categorical column to split/color the chart (must have ≤ 20 unique values).
- insight: 1 compelling sentence explaining WHY this chart is valuable for this specific data.
- title: short, descriptive chart title.

Return ONLY a valid JSON array of exactly 6 objects, nothing else, no markdown:
[
  {{
    "title":      "string",
    "chart_type": "bar|line|scatter|histogram|box|violin|pie|heatmap_corr",
    "x_col":      "column_name_or_null",
    "y_col":      "column_name_or_null",
    "color_col":  "column_name_or_null",
    "agg":        "count|sum|mean|median|min|max|null",
    "insight":    "one sentence"
  }},
  ...
]"""

        # ── API key check ─────────────────────────────────────────
        _api_key_d9 = st.session_state.get("gemini_api_key", "").strip()
        _ai_d       = st.session_state.get("ai_strategy")

        # Top banner: AI strategy summary if loaded
        if _ai_d and not _ai_d.get("error"):
            _conf   = _ai_d.get("confidence","MEDIUM")
            _conf_c = {"HIGH":"#00e5a0","MEDIUM":"#ffb347","LOW":"#ff4444"}.get(_conf,"#4a6070")
            _conf_bg= {"HIGH":"#061a10","MEDIUM":"#1a1008","LOW":"#1a0808"}.get(_conf,"#0c1014")
            _exec   = _ai_d.get("executive_summary","")
            _risks  = _ai_d.get("risk_flags",[])
            _perms  = _ai_d.get("permissions",{})
            n_apply = sum(1 for v in _perms.values() if v)
            n_skip  = sum(1 for v in _perms.values() if not v)

            st.markdown(
                f"<div class=\"anim-up\" style=\"background:{_conf_bg};border:1px solid {_conf_c}33;"
                f"border-left:4px solid {_conf_c};border-radius:10px;padding:1.2rem 1.5rem;margin-bottom:1rem;\">"
                f"<div style=\"display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;margin-bottom:0.6rem;\">"
                f"<span style=\"font-size:1.2rem;\">&#129302;</span>"
                f"<span class=\"card-title\" style=\"font-family:Syne,'Syne',sans-serif;font-size:1rem;"
                f"font-weight:800;color:#dce8f0;\">AI Strategy Active</span>"
                f"<span style=\"margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:0.52rem;"
                f"color:{_conf_c};border:1px solid {_conf_c}44;padding:2px 9px;border-radius:20px;\">"
                f"{_conf} CONFIDENCE</span>"
                f"<span style=\"font-family:'JetBrains Mono',monospace;font-size:0.52rem;"
                f"color:#00e5a0;border:1px solid #00e5a044;padding:2px 9px;border-radius:20px;\">"
                f"&#10003; {n_apply} apply</span>"
                f"<span style=\"font-family:'JetBrains Mono',monospace;font-size:0.52rem;"
                f"color:#ff6060;border:1px solid #ff606044;padding:2px 9px;border-radius:20px;\">"
                f"&#10007; {n_skip} skip</span></div>"
                f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.72rem;"
                f"color:#b0c8d0;line-height:1.8;\">{_E(_exec)}</div>"
                + (
                    "<div style=\"display:flex;flex-wrap:wrap;gap:0.35rem;margin-top:0.7rem;\">"
                    + "".join(
                        f"<span style=\"background:#1a1008;border:1px solid #ffb34733;border-radius:4px;"
                        f"padding:2px 9px;font-size:0.6rem;color:#ffb347;\">&#9873; {_E(r)}</span>"
                        for r in _risks[:5]
                    )
                    + "</div>"
                    if _risks else ""
                )
                + "</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div style=\"background:#0c1014;border:1px solid #1c2a35;border-radius:8px;"
                "padding:0.9rem 1.2rem;margin-bottom:1rem;display:flex;align-items:center;gap:0.8rem;\">"
                "<span style=\"font-size:1.1rem;\">&#129302;</span>"
                "<span style=\"font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#4a6070;\">"
                "No cleaning strategy loaded yet. Go to "
                "<b style=\"color:#dce8f0;\">Smart Clean → AI Advisor</b> to generate one.</span></div>",
                unsafe_allow_html=True
            )

        st.markdown("---")

        # ══════════════════════════════════════════════════════════
        # AI CHART GENERATION SECTION
        # ══════════════════════════════════════════════════════════
        st.markdown(
            "<div class=\"anim-up\" style=\"background:linear-gradient(135deg,#060f14,#091820);"
            "border:1px solid #00e5a033;border-radius:10px;padding:1.4rem 1.6rem;margin-bottom:1.2rem;\">"
            "<div style=\"display:flex;align-items:center;gap:0.7rem;margin-bottom:0.6rem;\">"
            "<span style=\"font-size:1.5rem;\">&#128202;</span>"
            "<div>"
            "<div class=\"card-title\" style=\"font-family:Syne,'Syne',sans-serif;font-size:1.1rem;"
            "font-weight:800;color:#dce8f0;\">AI-Generated Chart Intelligence</div>"
            "<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#4a6070;"
            "margin-top:0.2rem;\">Gemini analyzes your data profile and recommends the 6 most "
            "insightful visualizations — then renders them automatically.</div>"
            "</div></div>"
            "<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:#2a7050;"
            "line-height:1.7;\">"
            "&#9656; AI reads column names, types, cardinality, skewness, null rates &amp; sample values<br>"
            "&#9656; Picks the highest-value chart type for each pattern it detects<br>"
            "&#9656; Explains WHY each chart is valuable for your specific dataset"
            "</div></div>",
            unsafe_allow_html=True
        )

        # API key input (reuse sidebar key or let user enter here)
        if not _api_key_d9:
            st.markdown(
                "<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.68rem;"
                "color:#ffb347;margin-bottom:0.3rem;\">&#9888; Enter your Gemini API key to unlock AI charts "
                "(same key used in Smart Clean):</div>",
                unsafe_allow_html=True
            )
            _api_key_d9 = st.text_input(
                "Gemini API key", type="password",
                placeholder="AIzaSy…",
                key="dash_gemini_key",
                label_visibility="collapsed"
            )

        btn_col, info_col = st.columns([2, 3])
        with btn_col:
            gen_ai_charts = st.button(
                "✨ Generate AI Charts",
                key="gen_ai_charts_btn",
                use_container_width=True,
                disabled=not bool(_api_key_d9),
            )
        with info_col:
            st.markdown(
                "<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.62rem;"
                "color:#3a5060;padding-top:0.55rem;line-height:1.6;\">"
                "Uses ~500 tokens per generation &nbsp;·&nbsp; Free tier: 1,500 req/day"
                "<br>Key never stored permanently — get one at "
                "<a href='https://aistudio.google.com' target='_blank' "
                "style=\"color:#00e5a0;\">aistudio.google.com</a></div>",
                unsafe_allow_html=True
            )

        # ── Trigger AI call ────────────────────────────────────────
        if gen_ai_charts and _api_key_d9:
            with st.spinner("🤖 Gemini is analyzing your dataset and selecting the best charts…"):
                try:
                    _profile = _build_profile(dash_df)
                    _prompt  = _CHART_PROMPT_TEMPLATE.format(
                        profile=_json.dumps(_profile, indent=2, default=str)
                    )
                    _raw     = _gemini_call(_prompt, _api_key_d9)
                    _charts  = _parse_charts_json(_raw)
                    st.session_state["ai_chart_suggestions"] = _charts
                    st.session_state["ai_chart_error"]       = None
                except Exception as _e:
                    st.session_state["ai_chart_suggestions"] = None
                    st.session_state["ai_chart_error"]       = str(_e)

        # ── Render results ─────────────────────────────────────────
        _chart_err  = st.session_state.get("ai_chart_error")
        _chart_sugg = st.session_state.get("ai_chart_suggestions")

        if _chart_err:
            st.markdown(
                f"<div style=\"background:#1a0808;border:1px solid #ff444433;border-left:4px solid #ff4444;"
                f"border-radius:8px;padding:1rem 1.2rem;font-family:'JetBrains Mono',monospace;"
                f"font-size:0.72rem;color:#ff8080;\">&#9888; {_E(_chart_err)}</div>",
                unsafe_allow_html=True
            )

        elif _chart_sugg:
            st.markdown(
                f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.65rem;"
                f"color:#2a6050;margin-bottom:1rem;\">&#10003; Gemini suggested "
                f"{len(_chart_sugg)} charts based on your dataset profile:</div>",
                unsafe_allow_html=True
            )

            # render every suggested chart
            for _ci, _c in enumerate(_chart_sugg):
                _ct       = (_c.get("chart_type") or "bar").lower()
                _title    = _c.get("title", f"Chart {_ci+1}")
                _x        = _c.get("x_col")
                _y        = _c.get("y_col")
                _clr      = _c.get("color_col")
                _agg      = _c.get("agg") or "count"
                _insight  = _c.get("insight","")

                # validate columns exist
                _x   = _x   if _x   and _x   in dash_df.columns else None
                _y   = _y   if _y   and _y   in dash_df.columns else None
                _clr = _clr if _clr and _clr in dash_df.columns else None

                # insight banner
                st.markdown(
                    f"<div class=\"anim-up\" style=\"background:#0a1820;border:1px solid #1c3a5077;"
                    f"border-left:4px solid {accent_color};border-radius:8px;"
                    f"padding:0.85rem 1.1rem;margin-top:1.2rem;margin-bottom:0.4rem;"
                    f"display:flex;align-items:flex-start;gap:0.8rem;\">"
                    f"<span style=\"font-size:1.2rem;flex-shrink:0;\">&#128161;</span>"
                    f"<div>"
                    f"<div class=\"card-title\" style=\"font-family:Syne,'Syne',sans-serif;"
                    f"font-size:0.9rem;font-weight:800;color:#dce8f0;margin-bottom:0.25rem;\">"
                    f"{_E(_title)}</div>"
                    f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.65rem;"
                    f"color:#4a7890;line-height:1.6;\">{_E(_insight)}</div>"
                    f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.55rem;"
                    f"color:#2a5060;margin-top:0.35rem;\">"
                    f"type: <span style=\"color:#00e5a088;\">{_ct}</span>"
                    + (f" &nbsp;·&nbsp; x: <span style=\"color:#dce8f088;\">{_x}</span>" if _x else "")
                    + (f" &nbsp;·&nbsp; y: <span style=\"color:#dce8f088;\">{_y}</span>" if _y else "")
                    + (f" &nbsp;·&nbsp; agg: <span style=\"color:#ffb34788;\">{_agg}</span>" if _agg and _agg != "null" else "")
                    + (f" &nbsp;·&nbsp; color: <span style=\"color:#c084fc88;\">{_clr}</span>" if _clr else "")
                    + "</div></div></div>",
                    unsafe_allow_html=True
                )

                try:
                    _fig = None
                    _num_c = dash_df.select_dtypes(include=[np.number]).columns.tolist()
                    _cat_c = dash_df.select_dtypes(include=["object","category"]).columns.tolist()

                    if _ct == "histogram":
                        _col = _x if _x and _x in _num_c else (_num_c[0] if _num_c else None)
                        if _col:
                            _fig = px.histogram(dash_df, x=_col, nbins=35, color=_clr,
                                                color_discrete_sequence=color_seq,
                                                title=_title, template="plotly_dark")

                    elif _ct == "bar":
                        if _x and _y and _y in _num_c:
                            _agg_fn = _agg if _agg in ("sum","mean","median","min","max","count") else "count"
                            if _agg_fn == "count":
                                _agg_df = dash_df.groupby(_x, observed=True)[_y].count().nlargest(20).reset_index()
                            else:
                                _agg_df = dash_df.groupby(_x, observed=True)[_y].agg(_agg_fn).nlargest(20).reset_index()
                            _fig = px.bar(_agg_df, x=_x, y=_y, color=_x,
                                          color_discrete_sequence=color_seq,
                                          title=_title, template="plotly_dark")
                            _fig.update_layout(showlegend=False)
                        elif _x:
                            _vc = dash_df[_x].value_counts().head(20)
                            _fig = px.bar(x=_vc.index, y=_vc.values,
                                          labels={"x": _x, "y": "Count"},
                                          color=_vc.values,
                                          color_continuous_scale=[[0,"#0c1014"],[1, accent_color]],
                                          title=_title, template="plotly_dark")
                            _fig.update_layout(coloraxis_showscale=False)

                    elif _ct == "line":
                        if _x and _y and _y in _num_c:
                            _fig = px.line(dash_df.sort_values(_x), x=_x, y=_y, color=_clr,
                                           color_discrete_sequence=color_seq,
                                           title=_title, template="plotly_dark")

                    elif _ct == "scatter":
                        if _x and _y and _x in _num_c and _y in _num_c:
                            _fig = px.scatter(dash_df, x=_x, y=_y, color=_clr,
                                              color_discrete_sequence=color_seq,
                                              opacity=0.6, trendline="ols" if len(dash_df) < 50000 else None,
                                              title=_title, template="plotly_dark")

                    elif _ct == "box":
                        _yb = _y if _y and _y in _num_c else (_num_c[0] if _num_c else None)
                        _xb = _x if _x and _x in _cat_c else _clr
                        if _yb:
                            _fig = px.box(dash_df, x=_xb, y=_yb, color=_xb,
                                          color_discrete_sequence=color_seq,
                                          title=_title, template="plotly_dark")

                    elif _ct == "violin":
                        _yv = _y if _y and _y in _num_c else (_num_c[0] if _num_c else None)
                        _xv = _x if _x and _x in _cat_c else _clr
                        if _yv:
                            _fig = px.violin(dash_df, x=_xv, y=_yv, color=_xv,
                                             color_discrete_sequence=color_seq, box=True,
                                             title=_title, template="plotly_dark")

                    elif _ct == "pie":
                        _pc = _x if _x and _x in _cat_c else (_cat_c[0] if _cat_c else None)
                        if _pc:
                            _pv = dash_df[_pc].value_counts().head(12)
                            _fig = px.pie(values=_pv.values, names=_pv.index,
                                          color_discrete_sequence=color_seq,
                                          title=_title, template="plotly_dark")

                    elif _ct == "heatmap_corr":
                        _hc = [c for c in _num_c if c in dash_df.columns][:15]
                        if len(_hc) >= 2:
                            _cm  = dash_df[_hc].corr()
                            _fig = px.imshow(_cm, text_auto=".2f",
                                             color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                                             title=_title, template="plotly_dark")

                    if _fig:
                        _fig.update_layout(
                            height=440,
                            margin=dict(t=55, b=25, l=20, r=20),
                            paper_bgcolor="#060809",
                            plot_bgcolor="#0c1014",
                            font=dict(family="JetBrains Mono, monospace",
                                      color="#dce8f0", size=11),
                        )
                        _fig.update_traces(marker_line_width=0)
                        st.plotly_chart(_fig, use_container_width=True)
                    else:
                        st.markdown(
                            f"<div style=\"background:#0c1014;border:1px solid #1c2a35;border-radius:6px;"
                            f"padding:0.8rem 1rem;font-family:'JetBrains Mono',monospace;"
                            f"font-size:0.65rem;color:#3a5060;\">&#9888; Could not render this chart "
                            f"— column(s) not found or incompatible type.<br>"
                            f"Suggested: x={_E(str(_c.get('x_col')))}, "
                            f"y={_E(str(_c.get('y_col')))}</div>",
                            unsafe_allow_html=True
                        )
                except Exception as _fe:
                    st.markdown(
                        f"<div style=\"background:#160606;border:1px solid #ff444433;border-radius:6px;"
                        f"padding:0.7rem 1rem;font-family:'JetBrains Mono',monospace;"
                        f"font-size:0.65rem;color:#ff8080;\">Chart error: {_E(str(_fe))}</div>",
                        unsafe_allow_html=True
                    )

            # ── Regenerate button ──────────────────────────────────
            st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Regenerate Charts", key="regen_ai_charts", use_container_width=False):
                st.session_state.pop("ai_chart_suggestions", None)
                st.rerun()

        else:
            if not _chart_err:
                # Empty state — show what the feature does
                st.markdown(
                    "<div style=\"background:#0c1014;border:1px dashed #1c3a35;border-radius:10px;"
                    "padding:3rem 2rem;text-align:center;\">"
                    "<div style=\"font-size:3.5rem;margin-bottom:1rem;\">&#128202;</div>"
                    "<div class=\"card-title\" style=\"font-family:Syne,'Syne',sans-serif;"
                    "font-size:1.1rem;font-weight:800;color:#dce8f0;margin-bottom:0.7rem;\">"
                    "Click Generate AI Charts</div>"
                    "<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.72rem;"
                    "color:#4a6070;max-width:480px;margin:0 auto;line-height:1.85;\">"
                    "Gemini will inspect your dataset profile and select the <b style=\"color:#00e5a0;\">"
                    "6 highest-value visualizations</b> specifically for your data —<br>"
                    "distributions, correlations, outlier patterns, category breakdowns, "
                    "trend lines and more.<br><br>"
                    "<span style=\"color:#2a5060;\">Every chart comes with an AI-written insight "
                    "explaining what it reveals.</span></div></div>",
                    unsafe_allow_html=True
                )


    # ══════════════════════════════════════════════════════════════
    # D-TAB 10 — EXPORT DASHBOARD (downloadable HTML report)
    # ══════════════════════════════════════════════════════════════
    with d_tab10:
        st.markdown(_sec("📥", "Export Dashboard"), unsafe_allow_html=True)
        st.markdown(
            "<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.72rem;"
            "color:#4a6070;line-height:1.75;margin-bottom:1rem;\">Generate a complete "
            "standalone HTML report containing all charts, statistics and AI insights. "
            "Anyone can open it in a browser — no Python, no server needed.</div>",
            unsafe_allow_html=True
        )

        exp_l, exp_r = st.columns(2)
        with exp_l:
            exp_title   = st.text_input("Report title", "Data Intelligence Report", key="exp_title")
            exp_author  = st.text_input("Author / Team (optional)", "", key="exp_author")
        with exp_r:
            exp_include = st.multiselect("Charts to include",
                ["Distribution (all numeric)", "Correlation heatmap",
                 "Missing values map", "Outlier box plots",
                 "Top 15 values per category", "Quality gauge"],
                default=["Distribution (all numeric)", "Correlation heatmap",
                         "Missing values map", "Quality gauge"],
                key="exp_charts")

        if st.button("🪄 Generate Report", key="gen_report", use_container_width=False):
            with st.spinner("Building HTML report…"):
                try:
                    import plotly.io as pio
                    chart_divs = []

                    def _chart_section(title, fig):
                        html_chart = pio.to_html(fig, full_html=False, include_plotlyjs=False)
                        return (f"<div class='section'><h2>{title}</h2>{html_chart}</div>")

                    if "Distribution (all numeric)" in exp_include and num_cols:
                        for nc in num_cols[:6]:
                            s_nc = dash_df[nc].dropna()
                            if len(s_nc) > 0:
                                fig_e = px.histogram(s_nc, nbins=30, title=f"Distribution — {nc}",
                                                     template="plotly_dark",
                                                     color_discrete_sequence=[accent_color])
                                fig_e.update_layout(height=340, paper_bgcolor="#060809",
                                                    plot_bgcolor="#0c1014")
                                chart_divs.append(_chart_section(f"Distribution: {nc}", fig_e))

                    if "Correlation heatmap" in exp_include and len(num_cols) >= 2:
                        corr_e = dash_df[num_cols[:10]].corr()
                        fig_ce = px.imshow(corr_e, text_auto=".2f",
                                           color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                                           title="Correlation Matrix", template="plotly_dark")
                        fig_ce.update_layout(height=480, paper_bgcolor="#060809", plot_bgcolor="#0c1014")
                        chart_divs.append(_chart_section("Correlation Matrix", fig_ce))

                    if "Missing values map" in exp_include:
                        null_e = pd.DataFrame({"Column": dash_df.columns,
                                               "Missing %": (dash_df.isnull().mean()*100).round(2).values})
                        null_e = null_e[null_e["Missing %"] > 0]
                        if not null_e.empty:
                            fig_ne = px.bar(null_e, x="Column", y="Missing %",
                                            color="Missing %",
                                            color_continuous_scale=[[0,accent_color],[1,"#ff4444"]],
                                            title="Missing Values %", template="plotly_dark")
                            fig_ne.update_layout(height=340, paper_bgcolor="#060809",
                                                 plot_bgcolor="#0c1014", coloraxis_showscale=False)
                            chart_divs.append(_chart_section("Missing Values", fig_ne))

                    if "Outlier box plots" in exp_include and num_cols:
                        fig_oe = go.Figure()
                        for i, nc in enumerate(num_cols[:8]):
                            fig_oe.add_trace(go.Box(y=dash_df[nc], name=nc,
                                                     marker_color=color_seq[i % len(color_seq)],
                                                     boxmean="sd"))
                        fig_oe.update_layout(height=400, title="Outlier Overview",
                                              template="plotly_dark", paper_bgcolor="#060809",
                                              plot_bgcolor="#0c1014")
                        chart_divs.append(_chart_section("Outliers", fig_oe))

                    if "Top 15 values per category" in exp_include and cat_cols:
                        for cc in cat_cols[:4]:
                            top_e = dash_df[cc].value_counts().head(15)
                            fig_te = px.bar(x=top_e.index, y=top_e.values,
                                            title=f"Top 15 — {cc}", template="plotly_dark",
                                            color_discrete_sequence=[accent_color])
                            fig_te.update_layout(height=320, paper_bgcolor="#060809",
                                                 plot_bgcolor="#0c1014")
                            chart_divs.append(_chart_section(f"Top Values: {cc}", fig_te))

                    if "Quality gauge" in exp_include:
                        sc_b = report["health_score"]
                        gr_b = report["health_grade"]
                        gc   = {"A":"#00e5a0","B":"#7eb8f7","C":"#ffb347","D":"#ff4444"}.get(gr_b,"#dce8f0")
                        fig_qe = go.Figure(go.Indicator(
                            mode="gauge+number", value=sc_b,
                            title={"text": f"Health Score · Grade {gr_b}",
                                   "font": {"size": 14, "color": "#4a6070"}},
                            number={"suffix": "%", "font": {"size": 44, "color": gc}},
                            gauge={"axis": {"range": [0,100]}, "bar": {"color": gc},
                                   "bgcolor": "#0c1014",
                                   "steps": [{"range":[0,55],"color":"#1a0808"},
                                             {"range":[55,75],"color":"#1a1008"},
                                             {"range":[75,100],"color":"#061a10"}]}))
                        fig_qe.update_layout(height=300, paper_bgcolor="#060809")
                        chart_divs.append(_chart_section("Data Quality Score", fig_qe))

                    # AI section
                    ai_html = ""
                    _ai_exp = st.session_state.get("ai_strategy")
                    if _ai_exp and not _ai_exp.get("error"):
                        _ec = {"HIGH":"#00e5a0","MEDIUM":"#ffb347","LOW":"#ff4444"}.get(_ai_exp.get("confidence","MEDIUM"),"#4a6070")
                        ai_html = (
                            f"<div class='section'><h2>&#129302; AI Assessment</h2>"
                            f"<p style='color:{_ec};font-weight:600;'>Confidence: {_ai_exp.get('confidence','')}</p>"
                            f"<p>{_Hesc.escape(str(_ai_exp.get('executive_summary','')))}  </p>"
                        )
                        if _ai_exp.get("risk_flags"):
                            ai_html += "<h3>Risk Flags</h3><ul>"
                            for r in _ai_exp["risk_flags"]:
                                ai_html += f"<li>{_Hesc.escape(str(r))}</li>"
                            ai_html += "</ul>"
                        ai_html += "</div>"

                    # Stats table
                    stats_rows = ""
                    for col in dash_df.columns[:20]:
                        s_col = dash_df[col]
                        is_n  = pd.api.types.is_numeric_dtype(s_col)
                        stats_rows += (
                            f"<tr><td>{_Hesc.escape(col)}</td>"
                            f"<td>{str(s_col.dtype)}</td>"
                            f"<td>{s_col.isnull().sum()}</td>"
                            f"<td>{s_col.nunique()}</td>"
                            f"<td>{round(float(s_col.mean()),4) if is_n and len(s_col.dropna())>0 else 'N/A'}</td>"
                            f"<td>{round(float(s_col.std()),4)  if is_n and len(s_col.dropna())>1 else 'N/A'}</td></tr>"
                        )

                    from datetime import datetime as _dt
                    now_str     = _dt.now().strftime("%Y-%m-%d %H:%M")
                    author_str  = f"<p style='color:#4a6070;'>Author: {_Hesc.escape(exp_author)}</p>" if exp_author else ""

                    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_Hesc.escape(exp_title)}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=JetBrains+Mono:wght@400;600&display=swap');
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body{{ background:#060809; color:#dce8f0; font-family:'JetBrains Mono',monospace; padding:2rem; }}
  h1{{ font-family:Syne,sans-serif; font-size:2rem; font-weight:800; color:#dce8f0;
       border-left:4px solid #00e5a0; padding-left:1rem; margin-bottom:0.3rem; }}
  h2{{ font-family:Syne,sans-serif; font-size:1.2rem; font-weight:800; color:#00e5a0;
       margin:1.5rem 0 0.6rem; padding-bottom:0.4rem; border-bottom:1px solid #1c2a35; }}
  h3{{ font-family:'JetBrains Mono',monospace; font-size:0.8rem; font-weight:600; color:#4a6070;
       letter-spacing:0.12em; text-transform:uppercase; margin:1rem 0 0.4rem; }}
  p{{ font-size:0.82rem; color:#c0d0d8; line-height:1.7; margin-bottom:0.6rem; }}
  .meta{{ font-size:0.7rem; color:#4a6070; margin-bottom:2rem; }}
  .section{{ background:#0c1014; border:1px solid #1c2a35; border-radius:8px;
             padding:1.5rem; margin-bottom:1.5rem; }}
  .kpis{{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:1rem; margin-bottom:1.5rem; }}
  .kpi{{ background:#0c1014; border:1px solid #1c2a35; border-top:2px solid #00e5a0;
         border-radius:6px; padding:1rem; }}
  .kpi-label{{ font-size:0.6rem; color:#4a6070; letter-spacing:0.14em; text-transform:uppercase; }}
  .kpi-val{{ font-size:1.6rem; font-weight:700; color:#00e5a0; margin-top:0.2rem; }}
  table{{ width:100%; border-collapse:collapse; font-size:0.75rem; margin-top:0.5rem; }}
  th{{ background:#111820; color:#4a6070; padding:0.5rem 0.7rem; text-align:left;
       font-size:0.62rem; letter-spacing:0.1em; text-transform:uppercase;
       border-bottom:1px solid #1c2a35; }}
  td{{ padding:0.45rem 0.7rem; border-bottom:1px solid #0f1a22; color:#c0d0d8; }}
  tr:hover td{{ background:#0a1820; }}
  ul{{ padding-left:1.2rem; color:#c09060; font-size:0.75rem; line-height:1.8; }}
</style>
</head>
<body>
<h1>{_Hesc.escape(exp_title)}</h1>
{author_str}
<div class="meta">Generated: {now_str} &nbsp;·&nbsp; {len(dash_df):,} rows × {len(dash_df.columns)} cols &nbsp;·&nbsp; Source: {dash_label}</div>

<div class="kpis">
  <div class="kpi"><div class="kpi-label">Rows</div><div class="kpi-val">{len(dash_df):,}</div></div>
  <div class="kpi"><div class="kpi-label">Columns</div><div class="kpi-val">{len(dash_df.columns)}</div></div>
  <div class="kpi"><div class="kpi-label">Health score</div><div class="kpi-val">{report['health_score']}%</div></div>
  <div class="kpi"><div class="kpi-label">Grade</div><div class="kpi-val">{report['health_grade']}</div></div>
  <div class="kpi"><div class="kpi-label">Missing cells</div><div class="kpi-val">{int(dash_df.isnull().sum().sum()):,}</div></div>
</div>

{ai_html}

{''.join(chart_divs)}

<div class='section'>
<h2>&#128202; Column Summary</h2>
<table>
<tr><th>Column</th><th>Dtype</th><th>Nulls</th><th>Unique</th><th>Mean</th><th>Std</th></tr>
{stats_rows}
</table>
</div>

<p style="color:#2a3a42;text-align:center;margin-top:2rem;font-size:0.62rem;">
  Data Intelligence Engine — Generated with DataAuditor v4
</p>
</body>
</html>"""

                    st.success(f"✅ Report generated — {len(chart_divs)} chart(s) included")
                    st.download_button(
                        label="⬇ Download HTML Report",
                        data=full_html.encode("utf-8"),
                        file_name=f"dashboard_report_{_dt.now().strftime('%Y%m%d_%H%M')}.html",
                        mime="text/html",
                        key="dl_html_report",
                    )

                    # Preview
                    with st.expander("👁 Preview report structure", expanded=False):
                        st.markdown(
                            f"<div style=\"font-family:'JetBrains Mono',monospace;font-size:0.7rem;"
                            f"color:#4a6070;line-height:1.8;\">"
                            f"&#128203; Title: <span style=\"color:#dce8f0;\">{_Hesc.escape(exp_title)}</span><br>"
                            f"&#128202; Charts: <span style=\"color:#00e5a0;\">{len(chart_divs)}</span><br>"
                            f"&#129302; AI section: <span style=\"color:{'#00e5a0' if ai_html else '#4a6070'};\">"
                            f"{'Included' if ai_html else 'Not loaded'}</span><br>"
                            f"&#128196; File size: ~{len(full_html)//1024} KB"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                except Exception as exp_err:
                    st.error(f"Export failed: {exp_err}")




st.markdown(
    "<div style='font-family:\"JetBrains Mono\",monospace;font-size:0.62rem;"
    "color:#2a3a42;letter-spacing:0.15em;text-align:center;padding:1rem 0;'>"
    "DATA INTELLIGENCE ENGINE &nbsp;·&nbsp; POWERED BY DATAAUDITOR v4"
    "</div>",
    unsafe_allow_html=True
)
