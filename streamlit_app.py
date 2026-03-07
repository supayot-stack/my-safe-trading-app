import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. CORE LOGIC (สมองของระบบ) ---
# แยกฟังก์ชันคำนวณออกมา เพื่อให้เรียกใช้ซ้ำได้ง่ายและทดสอบ (Unit Test) ได้
def calculate_indicators(df):
    # ใช้ Vectorized Operations ของ Pandas (เร็วที่สุด)
    df['SMA200'] = df['Close'].rolling(200).mean()
    df['SMA50'] = df['Close'].rolling(50).mean()
    
    # RSI Calculation
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    
    # ATR & Stop-Loss
    high_low = df['High'] - df['Low']
    high_cp = np.abs(df['High'] - df['Close'].shift())
    low_cp = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    df['SL'] = df['Close'] - (df['ATR'] * 2.5)
    return df

# --- 2. DATA PROVIDER ---
@st.cache_data(ttl=3600) # Cache 1 ชม. เพื่อลดการ Load
def fetch_data(ticker):
    try:
        # ตัดระบบเช็ค List ออก ให้ User จัดการ Ticker เอง
        data = yf.download(ticker, period="2y", interval="1d", progress=False)
        if data.empty: return None
        return calculate_indicators(data)
    except:
        return None

# --- 3. UI LAYER ---
st.title("🚀 Clean Quant Terminal")

# ใช้ Sidebar เก็บ Global Settings
with st.sidebar:
    tickers = st.text_input("Enter Tickers (comma separated):", "NVDA, AAPL, PTT.BK").upper().split(",")

# ส่วนการแสดงผล (Main)
if tickers:
    summary_data = []
    for t in tickers:
        t = t.strip()
        df = fetch_data(t)
        if df is not None:
            last = df.iloc[-1]
            summary_data.append({
                "Symbol": t,
                "Price": last['Close'],
                "RSI": last['RSI'],
                "Signal": "BUY" if last['Close'] > last['SMA200'] and last['RSI'] < 40 else "WAIT"
            })
    
    st.table(pd.DataFrame(summary_data))
