import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Scanner Pro", layout="wide")
st.title("🛡️ Safe Heaven Scanner (Multi-Timeframe)")

# --- 2. แถบเมนูข้าง ---
st.sidebar.header("⚙️ Settings")

# เลือกสินทรัพย์
assets = st.sidebar.multiselect(
    "เลือกสินทรัพย์:", 
    ["^GSPC", "^SET50.BK", "BTC-USD", "ETH-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"],
    default=["^GSPC", "BTC-USD"]
)

# เลือกหน่วยเวลา (Interval)
interval_opt = {
    "1 นาที": "1m",
    "5 นาที": "5m",
    "15 นาที": "15m",
    "1 ชั่วโมง": "1h",
    "1 วัน": "1d"
}
selected_interval = st.sidebar.selectbox("เลือกหน่วยเวลา:", list(interval_opt.keys()), index=4)
interval_code = interval_opt[selected_interval]

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

@st.cache_data(ttl=30)
def fetch_data(tickers, interval):
    results = []
    # กำหนดระยะเวลาย้อนหลังตาม Interval เพื่อให้มีข้อมูลพอคำนวณ SMA200
    period = "2y" if interval == "1d" else "60d" 
    if interval in ["1m", "5m"]: period = "7d"

    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 200: continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            last_price = float(last['Close'])
            prev_price = float(prev['Close'])
            change_pct = ((last_price - prev_price) / prev_price) * 100
            
            # ตรรกะสัญญาณ
            if last_price > float(last['SMA200']) and float(last['RSI']) < 40:
                action = "🟢 BUY"
            elif float(last['RSI']) > 75:
                action = "💰 PROFIT"
            elif last_price < float(last['SMA200']):
                action = "🔴 EXIT"
            else:
                action = "Wait"
                
            results.append({
                "Ticker": ticker,
                "Price": f"{last_price:,.2f}",
                "Change %": f"{change_pct:.2f}%",
                "RSI": round(float(last['RSI']), 2),
                "Action": action
            })
        except: continue
    return pd.DataFrame(results)

# --- 4. การแสดงผล ---
if assets
