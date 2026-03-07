import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ULTRA DARK UI CONFIG ---
st.set_page_config(page_title="Institutional Quant Terminal", layout="wide")
st.markdown("""
    <style>
    /* พื้นหลังดำสนิท */
    .stApp { background-color: #000000; color: #ffffff; }
    
    /* การ์ดสไตล์ Terminal */
    .stat-card { 
        background-color: #0a0a0a; padding: 20px; border-radius: 4px; 
        border: 1px solid #1e1e1e; border-left: 4px solid #007bff;
        margin-bottom: 20px;
    }
    
    /* Portfolio Card */
    .portfolio-card {
        background-color: #050505; padding: 15px; border-radius: 4px;
        border: 1px solid #1e1e1e; margin-bottom: 10px;
    }
    
    /* สีเน้นสถานะ */
    .profit { color: #00ff66; font-weight: bold; text-shadow: 0 0 5px #00ff66; }
    .loss { color: #ff3333; font-weight: bold; text-shadow: 0 0 5px #ff3333; }
    
    /* ปรับแต่ง Sidebar */
    section[data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid #1e1e1e; }
    
    /* ปรับแต่ง Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #000000; }
    .stTabs [data-baseweb="tab"] { color: #444; }
    .stTabs [aria-selected="true"] { color: #ffffff; border-bottom-color: #007bff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. QUANT ENGINE ---
@st.cache_data(ttl=3600)
def get_institutional_data(ticker):
    try:
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper():
            thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF"]
            if ticker in thai_list: ticker += ".BK"
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Trend & RSI
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # ATR Risk Mgmt
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5) 
        df['TP'] = df['Close'] + (df['ATR'] * 5.0) 
        df['Vol_Ratio'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-9)
        return df.dropna()
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("### 🏦 TERMINAL CONTROL")
    equity = st.number_input("Total Equity (THB):", value=1000000)
    max_risk = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0, 0.1)
    st.divider()
    watchlist = st.multiselect("Watchlist:", ["NVDA", "AAPL", "BTC-USD", "SET50.BK", "GOLD"], default=["NVDA", "BTC-USD"])
    custom = st.text_input("➕ Add Ticker:").upper().strip()
    final_watchlist = list(watchlist)
    if custom and custom not in final_watchlist: final_watchlist.append(custom)

# --- 4. DATA PROCESSING ---
results = []
data_dict = {}
if final_watchlist:
    for ticker in final_watchlist:
        df = get_institutional_data(ticker)
        if df is not None:
            data_dict[ticker] = df
            l = df.iloc[-1]
            p, r, s200, vr = l['Close'], l['RSI'], l['SMA200'], l['Vol_Ratio']
            if p > s200 and r < 45 and vr > 1.2: signal = "🟢 ACCUMULATE"
            elif r > 75: signal = "💰 DISTRIBUTION"
            elif p < s200: signal = "🔴 BEARISH"
            else: signal = "⚪ NEUTRAL"
            sl_gap = p - l['SL']
            qty = int((equity * (max_risk/100)) / sl_gap) if sl_gap > 0 else 0
            results.append({"Asset": ticker, "Price": round(p, 2), "Regime": signal, "RSI": round(r, 1), "Vol-Force": f"{vr:.2f}x", "Target Qty": f"{qty:,}", "SL": round(l['SL'], 2)})

# --- 5. MAIN TERMINAL ---
t1, t2, t3, t4 = st.tabs(["🏛 SCANNER", "📈 CHARTS", "💼 PORTFOLIO", "📖 GUIDE"])

with t1:
    st.markdown("### 🏛 Market Order Flow")
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Equity", f"{equity:,.0f} ฿")
        c2.metric("Risk Budget", f"{(equity*max_risk/100):,.0f
