import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. SETUP ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "TSLA"]

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # SMA & RSI
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # RVOL
        df['Vol_Avg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / (df['Vol_Avg'] + 1e-9)
        
        # Squeeze Logic
        df['MA20'] = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['UB'] = df['MA20'] + (2 * std)
        df['LB'] = df['MA20'] - (2 * std)
        
        tr = pd.concat([df['High']-df['Low'], 
                        (df['High']-df['Close'].shift(1)).abs(), 
                        (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(20).mean()
        df['UK'] = df['MA20'] + (1.5 * atr)
        df['LK'] = df['MA20'] - (1.5 * atr)
        df['Sqz'] = (df['LB
