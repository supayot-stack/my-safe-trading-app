import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Scanner", layout="wide")
st.title("🛡️ Safe Heaven Scanner (Fixed Mode)")

# --- 2. แถบเมนูข้าง ---
st.sidebar.header("⚙️ Settings")
assets = st.sidebar.multiselect(
    "เลือกสินทรัพย์ที่ต้องการ:", 
    ["^GSPC", "^SET50.BK", "BTC-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT", "PTT.BK", "AOT.BK"],
    default=["^GSPC", "^SET50.BK", "BTC-USD"]
)

# --- 3. ฟังก์ชันคำนวณ ---
def calculate_indicators(df):
    # SMA 200
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=60)
def fetch_data(tickers):
    results = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 200: 
                continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            last_price = float(last['Close'])
            prev_price = float(prev['Close'])
            change_pct = ((last_price - prev_price) / prev_price) * 100
            
            # ตรวจสอบการย่อหน้าในบล็อกเงื่อนไข (จุดที่เคย Error)
            if last_price > float(last['SMA200']) and float(last['RSI']) < 40:
                action = "🟢 BUY"
            elif float(last['RSI']) > 75:
