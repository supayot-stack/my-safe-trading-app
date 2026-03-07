import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="Hedge Fund Terminal V7.1", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .status-card { 
        background-color: #161b22; padding: 20px; border-radius: 10px; 
        border: 1px solid #30363d; border-top: 4px solid #58a6ff;
    }
    .metric-value { font-size: 1.2em; font-weight: bold; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NOTIFICATION ENGINE ---
def broadcast_discord(webhook_url, data):
    if not webhook_url: return
    color = 65280 if "ACCUMULATE" in data['Signal'] else 16711680
    embed = {
        "title": f"🏛️ Institutional Alert: {data['Asset']}",
        "color": color,
        "fields": [
            {"name": "Signal", "value": f"**{data['Signal']}**", "inline": True},
            {"name": "Price", "value": f"{data['Price']:,.2f}", "inline": True},
            {"name": "Score", "value": f"{data['Score']}/100", "inline": True},
            {"name": "Action", "value": f"Buy **{data['Qty']:,}** units", "inline": False},
            {"name": "Risk", "value": f"🚫 SL: {data['SL']:,.2f}\n🎯 TP: {data['TP']:,.2f}", "inline": True},
            {"name": "Fundamental", "value": f"P/E: {data['PE']}\nYield: {data['Yield']}", "inline": True}
        ]
    }
    try: requests.post(webhook_url, json={"embeds": [embed]})
    except: pass

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        # Smart Thai Ticker
        thai_core = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF"]
        if ticker in thai_core and "." not in ticker: ticker += ".BK"

        stock = yf.Ticker(ticker)
        df = stock.history(period="2y", interval="1d", auto_adjust=True)
        if df.empty or len(df) < 200: return None, "N/A", "N/A"
        
        # Fundamental (Safety handling)
        info = stock.info
        pe = info.get('trailingPE', 'N/A')
        div = info.get('dividendYield', 0)
        yield_str = f"{div*100:.2f}%" if div else "N/A"

        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        # ATR & RSI
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # ADX
        plus_dm = df['High'].diff().clip(lower=0)
        minus_dm = (-df['Low'].diff()).clip(lower=0)
        atr_14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.
