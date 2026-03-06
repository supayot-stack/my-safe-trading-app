import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. REDDIT STYLE CSS ---
st.set_page_config(page_title="QuantPro Dashboard", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #00d4ff; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    .main-header { font-size: 2.5rem; font-weight: 700; color: #ffffff; margin-bottom: 20px; }
    .guide-box { padding: 15px; border-radius: 10px; background-color: #161b22; border-left: 5px solid #00d4ff; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. ENGINE ---
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
        df['RVOL'] = df['Volume'] / (df['Volume'].rolling(20).mean() + 1e-9)
        
        m20 = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
        df['SQZ'] = (m20 - (2*std) > m20 - (1.5*tr.rolling(20).mean())) & (m20 + (2*std) < m20 + (1.5*tr.rolling(20).mean()))
        return df
    except: return None

# --- 3. SIDEBAR & SESSION ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["BTC-USD", "NVDA", "AAPL", "TSLA", "^SET50.BK"]

st.sidebar.title("🚀 QuantPro")
mode = st.sidebar.selectbox("Strategy Mode", ["Trend Follower", "Volume Hunter", "Volatility Squeeze"])
itv_map = {"1D": "1d", "1H": "1h", "5M": "5m"}
itv_code = itv_map[st.sidebar.select_slider("Timeframe", options=["5M", "1H", "1D"], value="1D")]

# --- 4. TOP SECTION: CHART & METRICS ---
st.markdown('<p class="main-header">🛡️ Safe Heaven Quant Pro</p>', unsafe_allow_html=True)

# Watchlist Selector
sel = st.selectbox("Select Asset to Analyze", st.session_state.my_watchlist)
df = fetch_data(sel, itv_code)

if df is not None:
    l = df.iloc[-1]
    # Reddit-style Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Price", f"{l['Close']:,.2f}")
    m2.metric("RSI (14)", f"{l['RSI']:.1f}")
    m3.metric("RVOL", f"{l['RVOL']:.2.1f}x")
    m4.metric("Status", "💎 SQUEEZE" if l['SQZ'] else "NORMAL")

    # High-End Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], name='SMA 200', line=dict(color='#ff9f43', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color
