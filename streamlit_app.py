import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven ClearView", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner (Fixed Version)")

# --- 2. การตั้งค่าหุ้นและหมวดหมู่ ---
stock_categories = {
    "🌍 Market Indices": ["^GSPC", "^SET50.BK", "GC=F"],
    "💻 Technology": ["NVDA", "AAPL", "MSFT", "GOOGL", "TSLA"],
    "🇹🇭 Thai & Finance": ["SCB.BK", "KBANK.BK", "PTT.BK", "AOT.BK"],
    "₿ Crypto": ["BTC-USD", "ETH-USD"]
}

all_assets = []
for stocks in stock_categories.values():
    all_assets.extend(stocks)

st.sidebar.header("⏱️ Timeframe")
interval_opt = {"1 นาที": "1m", "5 นาที": "5m", "1 ชั่วโมง": "1h", "1 วัน": "1d"}
selected_interval = st.sidebar.selectbox("เลือกหน่วยเวลา:", list(interval_opt.keys()), index=3)
interval_code = interval_opt[selected_interval]

# --- 3. ฟังก์ชันคำนวณ ---
def calculate_indicators(df):
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    delta = df
