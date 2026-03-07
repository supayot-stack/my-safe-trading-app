import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PRO UI CONFIG (ULTRA DARK) ---
st.set_page_config(page_title="Institutional Quant Terminal", layout="wide")
st.markdown("""
    <style>
    /* พื้นหลังดำสนิทแบบห้องเทรดสถาบัน */
    .stApp { background-color: #000000; color: #ffffff; }
    
    /* การ์ดสรุปข้อมูล */
    .stat-card { 
        background-color: #0a0a0a; padding: 20px; border-radius: 8px; 
        border: 1px solid #1e1e1e; border-top: 4px solid #007bff;
        margin-bottom: 20px;
    }
    
    /* การ์ดพอร์ตโฟลิโอ */
    .portfolio-card {
        background-color: #050505; padding: 15px; border-radius: 8px;
        border: 1px solid #1e1e1e; margin-bottom: 10px;
        border-left: 5px solid #00ff66;
    }

    /* คู่มือการใช้งาน */
    .guide-card {
        background-color: #0a0a0a; padding: 25px; border-radius: 10px;
        border: 1px solid #333; border-left: 5px solid #ffcc00;
        margin-top: 15px;
    }
    
    /* สีสถานะ */
    .profit { color: #00ff66; font-weight: bold; }
    .loss { color: #ff3333; font-weight: bold; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. QUANT ENGINE ---
@st.cache_data(ttl=3600)
def get_institutional_data(ticker):
    try:
        # Smart Thai logic
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper():
            thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF"]
            if ticker in thai_list: ticker += ".BK"

        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

        # ATR Risk Calculation
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5) 
        df['Vol_Ratio'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-9)

        return df.dropna()
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Quant Control")
    equity = st.number_input("Total Equity (THB):", value=1000000, step=10000)
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
    with st.spinner('Scanning Markets...'):
        for t in final_watchlist:
            df = get_institutional_data(t)
            if df is not None:
                data_dict[t] = df
                l = df.iloc[-1]
                p, r, s200, s50, vr = l['Close'], l['RSI'], l['SMA200'], l['SMA50'], l['Vol_Ratio']
                
                if p > s200 and r < 45 and vr > 1.2:
