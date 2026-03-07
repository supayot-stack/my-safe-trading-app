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
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_list: ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_cols): return None

        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        df['ATR'] = calculate_atr(df)
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        df['TP'] = df['Close'] + (df['ATR'] * 5)
        return df
    except: return None

# --- 3. ส่วนเมนู (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ ระบบหลังบ้าน"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # Sidebar
    st.sidebar.header("💰 ตั้งค่าพอร์ต")
    port_size = st.sidebar.number_input("เงินลงทุนทั้งหมด (บาท):", min_value=1000, value=100000)
    # แก้ไขจุดที่ Error: รวมข้อความเป็นบรรทัดเดียว
    risk_pct = st.sidebar.slider("ความเสี่ยงที่ยอมรับได้ต่อไม้ (%):", 0.1, 5.0, 1.0)
    
    st
