import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. Setup ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["PTT.BK", "BTC-USD", "NVDA", "AAPL"]

# --- 2. Data Engine ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # SMA & RSI
        df['SMA'] = df['Close'].rolling(200).mean()
        diff = df['Close'].diff()
        g = (diff.where(diff > 0, 0)).rolling(14).mean()
        l = (-diff.where(diff < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (g / (l + 1e-9))))
        
        # RVOL
        v_avg = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / (v_avg + 1e-9)
        
        # Squeeze (BB & KC)
        m20 = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['UB'] = m20 + (2 * std)
        df['LB'] = m20 - (2 * std)
        
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1)).abs()
