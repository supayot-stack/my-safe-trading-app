import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. SETTINGS & STYLE ---
st.set_page_config(page_title="QuantPro Dashboard", layout="wide")

# CSS สำหรับตกแต่งให้เหมือน Reddit Dashboard
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .guide-section {
        background-color: #0d1117;
        border-left: 4px solid #58a6ff;
        padding: 10px 20px;
        margin: 10px 0px;
        border-radius: 0 10px 10px 0;
    }
    .status-buy { color: #3fb950; font-weight: bold; }
    .status-exit { color: #f85149; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["BTC-USD", "NVDA", "AAPL", "TSLA", "^SET50.BK"]

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "max" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        df['RVOL'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-
