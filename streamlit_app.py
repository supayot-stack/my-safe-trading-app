import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Institutional Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stat-card { 
        background-color: #161b22; padding: 20px; border-radius: 8px; 
        border: 1px solid #30363d; border-top: 4px solid #58a6ff;
    }
    .portfolio-card {
        background-color: #0d1117; padding: 15px; border-radius: 8px;
        border: 1px solid #30363d; margin-bottom: 10px;
    }
    .profit { color: #3fb950; font-weight: bold; }
    .loss { color: #f85149; font-weight: bold; }
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
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5) 
        df['TP'] = df['Close'] + (df['ATR'] * 5.0) 
        df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
        return df.dropna()
    except: return None

# --- 3. SIDEBAR ---
