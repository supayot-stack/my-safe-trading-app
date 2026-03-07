import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ULTRA DARK UI ---
st.set_page_config(page_title="Institutional Quant V7.6", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #1e1e1e; }
    .stat-card { 
        background-color: #0a0a0a; padding: 20px; border-radius: 8px; 
        border: 1px solid #1e1e1e; border-top: 4px solid #007bff;
        margin-bottom: 20px;
    }
    div[data-testid="stMetricValue"] { color: #00ffcc; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. NOTIFICATION ENGINE ---
def send_discord(webhook, data):
    if not webhook: return
    color = 65280 if "ACC" in data['Regime'] else 16711680
    payload = {
        "embeds": [{
            "title": f"🏛️ Trade Alert: {data['Asset']}",
            "color": color,
            "fields": [
                {"name": "Signal", "value": data['Regime'], "inline": True},
                {"name": "Price", "value": str(data['Price']), "inline": True},
                {"name": "Quantity", "value": data['Qty'], "inline": False},
                {"name": "SL / TP", "value": f"🚫 {data['SL']} / 🎯 {data['TP']}", "inline": False}
            ]
        }]
    }
    try: requests.post(webhook, json=payload)
    except: pass

# --- 3. QUANT ENGINE (Fixed ATR Syntax) ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        # Smart Thai logic
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper():
            if ticker in ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB"]: ticker += ".BK"

        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 1. Trend Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()

        # 2. RSI Calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # 3. ATR Calculation (FIXED SYNTAX)
        h_l = df['High'] - df['Low']
        h_pc = abs(df['High'] - df['Close'].shift())
