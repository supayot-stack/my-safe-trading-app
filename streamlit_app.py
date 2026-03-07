import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING & ULTRA DARK CSS (FIXED SYNTAX) ---
st.set_page_config(page_title="Institutional Quant V7.5", layout="wide")

# แก้ไขจุดที่ทำให้เกิด SyntaxError โดยการตรวจสอบจุดปิดเครื่องหมาย """ ให้ชัดเจน
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
    .stTabs [data-baseweb="tab-list"] { background-color: #000000; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #ffffff; border-bottom-color: #007bff; }
</style>
""", unsafe_allow_html=True)

# --- 2. NOTIFICATION ENGINE ---
def send_discord(webhook, data):
    if not webhook: return
    color = 65280 if "ACC" in data['Regime'] else 16711680
    payload = {
        "embeds": [{
            "title": f"🏛️ Alert: {data['Asset']}",
            "color": color,
            "fields": [
                {"name": "Signal", "value": data['Regime'], "inline": True},
                {"name": "Price", "value": f"{data['Price']}", "inline": True},
                {"name": "Target Qty", "value": data['Qty'], "inline": False}
            ]
        }]
    }
    try: requests.post(webhook, json=payload)
    except: pass

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        # Smart Thai logic
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper():
            if ticker in ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB"]: ticker += ".BK"

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
        
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-
