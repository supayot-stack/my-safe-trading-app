import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .info-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันเสริมสำหรับการจัดการข้อมูล ---
def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_cp = np.abs(df['High'] - df['Close'].shift())
    low_cp = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def get_data(ticker, interval="1d", data_period="2y"):
    try:
        # ปรับชื่อ Ticker สำหรับตลาดไทย
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_list:
            ticker += ".BK"
        
        # ดึงข้อมูล
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        
        if df.empty:
            return None

        # --- แก้ปัญหาจอดำ: จัดการ Multi-Index Columns ---
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # ตรวจสอบว่าคอลัมน์สำคัญอยู่ครบไหม
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols):
            return None

        # --- คำนวณ Indicators ---
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # RSI Logic
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # Volume & ATR
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        df['ATR'] = calculate_atr(df)
        
        # Dynamic Risk Management (2.5x ATR)
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        df['TP'] = df['Close'] + (df['ATR'] * 5)
        
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

# --- 3. UI Layout ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ ระบบหลังบ้าน"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # Sidebar
    st.sidebar.header("💰 ตั้งค่าพอร์ต")
    port_size = st.sidebar.number_input("เงินลงทุน (บาท):", min_value=1000, value=100000)
    risk_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.1, 5.0, 1.0)
    
    st.sidebar.divider()
    default_assets = ["NVDA", "AAPL", "BTC-USD", "PTT.BK", "CPALL.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้น:", options=default_assets + ["TSLA", "GOOGL", "ETH-USD"], default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper()
    
    tickers = list(selected_assets)
    if custom_ticker: tickers.append(custom_ticker)

    # ประมวลผล
    results_list = []
    if tickers:
        with st.spinner('กำลังประมวลผลข้อมูล...'):
            for t in tickers:
                data = get_data(t)
                if data is not None and len(data) > 20:
                    last = data.iloc[-1]
                    
                    # Signal Logic
                    price, rsi, sma, vol, vol_avg = last['Close'], last['RSI'], last['SMA200'], last['Volume'], last['Vol_Avg5']
                    
                    if price > sma and
