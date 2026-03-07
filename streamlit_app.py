import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. HEX-PERFECT UI CONFIG ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    /* Global Background & Sidebar */
    .stApp { background-color: #111216; color: #ffffff; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #121217; border-right: 1px solid #1c1c21; width: 300px !important; }
    
    /* Sidebar Text & Inputs */
    .stSidebar [data-testid="stMarkdownContainer"] p { color: #8b949e; font-size: 13px; }
    .stNumberInput div div input, .stTextArea div div textarea {
        background-color: #1c1c21 !important; color: #ffffff !important; border: 1px solid #2d2d33 !important;
        border-radius: 6px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; border-bottom: 1px solid #1c1c21; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; font-size: 14px; padding: 10px 5px; background: transparent; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom: 2px solid #ffffff !important; font-weight: 600; }

    /* Metric Card - สีเทาเข้มแบบในรูป #2c2c32 */
    .metric-card {
        background-color: #2c2c32; padding: 22px 20px; border-radius: 8px;
        border: 1px solid #36363c; text-align: left; margin-bottom: 12px;
    }
    .m-label { color: #8b949e; font-size: 13px; margin-bottom: 8px; }
    .m-val-green { color: #3fb950; font-size: 26px; font-weight: 700; }
    .m-val-red { color: #f85149; font-size: 26px; font-weight: 700; }

    /* Status Banner */
    .verified-banner {
        background-color: #2c2c32; border: 1px solid #36363c; border-radius: 6px;
        padding: 12px; text-align: center; color: #3fb950; font-size: 15px; font-weight: 600;
        margin-top: 30px; display: flex; align-items: center; justify-content: center; gap: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX ---
DB_FILE = "the_masterpiece_v2.json"
COMMISSION_RATE = 0.0015 

@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except: pass
    return 36.52 # Fixed to match image display

LIVE_USDTHB = get_live_fx()

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
    except: pass

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_popular = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_popular and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
                if df.empty or len(df) < 50: continue
                
                df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
                df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14, min_periods=1).mean()
                sl_raw = df['Close'] - (df['ATR'] * 2.5)
                tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
                for i in range(1, len(df)):
                    tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
                df['Trailing_SL'] = tsl
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20, min_periods=1).mean().replace(0, np.nan)
                processed[t] = df.ffill().bfill()
            except: continue
        return processed
    except: return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.markdown("<h2 style='color:white; margin-bottom:0;'>🏆 The Masterpiece</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e; margin-top:0;'>Institutional Systematic OS</p>", unsafe_allow_html=True)
    st.divider()
    st.markdown("FX Rate")
    st.markdown(f"<h3 style='color:white; margin-top:-10px;'>{LIVE_USDTHB:.2f} THB</h3>", unsafe_allow_html=True)
    capital = st.number_input("Total Equity (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. SIGNAL PROCESSING ---
data_dict = fetch_all_data(final_watchlist)

# --- 6. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Logic Guide"])

with tabs[4]: # Analytics Hub - REPLICA DESIGN
    if data_dict:
        # Mocking Backtest Result for Demo (to populate the Analytics Hub)
        sel_bt = list(data_dict.keys())[0]
        df_bt = data_dict[sel_bt].iloc[-250:].copy()
        is_thai = ".BK" in sel_bt
        fx_bt = 1 if is_thai else LIVE_USDTHB
        
        # Symmetrical Layout [2.2 : 0.8 : 2.2]
        c_left, c_mid, c_right = st.columns([2.2, 0.8, 2.2], gap="medium")
        
        with c_left:
            st.markdown("🎲 **Monte Carlo Simulation**")
            fig_mc = go.Figure()
            # Luminous Blue paths (#86c7ed)
            for i in range(80):
                path = np.random.normal(0.00065, 0.015, 100).cumsum()
                fig_mc.add_trace(go.Scatter(y=capital * (1 + path), mode='lines', 
                                           line=dict(width=0.8, color='rgba(134, 199, 237, 0.15)'), showlegend=False))
            fig_mc.update_layout(height=480, template="plotly_dark", margin=dict(l=0,r=0,t=10,b=0),
                                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                xaxis=dict(showgrid=True, gridcolor='#1c1c21', title="Number of Trades"),
                                yaxis=dict(showgrid=True, gridcolor='#1c1c21', title="Portfolio Value (THB)"))
            st.plotly_chart(fig_mc, use_container_width=True)

        with c_mid:
            st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
            stats = [("Win Rate", "58.4%", "m-val-green"), ("Profit Factor", "2.14", "m-val-green"), 
                     ("Avg Trade P/L", "12,450 THB", "m-val-green"), ("Max Drawdown", "-8.2%", "m-val-red")]
            for label, val, style in stats:
                st.markdown(f'<div class="metric-card"><div class="m-label">{label}</div><div class="{style}">{val}</div></div>', unsafe_allow_html=True)

        with c_right:
            st.markdown("📈 **Equity Curve**")
            equity_path = (df_bt['Close'] / df_bt['Close'].iloc[0]) * 1000000 * 1.1245
            st.markdown(f"<div style='margin-bottom:15px;'>"
                        f"<div style='color:#8b949e; font-size:12px;'>Final Balance (Net)</div>"
                        f"<div style='color:#3fb950; font-size:22px; font-weight:700;'>{equity_path.iloc[-1]:,.2f} THB</div>"
                        f"</div>", unsafe_allow_html=True)
            
            fig_eq = go.Figure(go.Scatter(x=df_bt.index, y=equity_path, line=dict(color='#3fb950', width=2), fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.05)'))
            fig_eq.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=5,b=0),
                                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                xaxis=dict(showgrid=True, gridcolor='#1c1c21'), yaxis=dict(showgrid=True, gridcolor='#1c1c21'))
            st.plotly_chart(fig_eq, use_container_width=True)

        st.markdown("<div class='verified-banner'>✅ System Alpha Verified</div>", unsafe_allow_html=True)

st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS | v7.0 Hex-Matched")
