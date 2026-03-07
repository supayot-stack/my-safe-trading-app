import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTINGS & CSS ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .status-card { 
        background-color: #1e222d; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #30363d; 
        border-left: 5px solid #00ffcc;
    }
    .metric-val { color: #00ffcc; font-weight: bold; font-size: 1.2em; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE ---
@st.cache_data(ttl=3600)
def get_processed_data(ticker):
    try:
        # Auto-suffix for Thai Stocks
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB", "BDMS"]
        if ticker in thai_list and "." not in ticker: ticker += ".BK"
        
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. Trend: SMA 200
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # 2. RSI (Wilder's Standard)
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # 3. ATR (Volatility)
        high
