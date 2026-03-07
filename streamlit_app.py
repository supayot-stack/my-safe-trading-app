import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING ---
st.set_page_config(page_title="Safe Heaven Quant Pro ATR", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & ATR", "📖 คู่มือเทคนิค"])

with tab2:
    st.header("🛡️ ทำไมต้องใช้ ATR Stop Loss?")
    st.markdown("""
    ATR (Average True Range) คือค่าเฉลี่ยความกว้างของราคาหุ้นในแต่ละช่วงเวลา:
    - **หุ้นผันผวนสูง:** ATR จะกว้าง ระบบจะวางจุดหนี (SL) ให้ไกลขึ้นเพื่อกันโดนสะบัด
    - **หุ้นผันผวนต่ำ:** ATR จะแคบ ระบบจะวางจุดหนี (SL) ให้ใกล้ขึ้นเพื่อเพิ่มจำนวนหุ้น
    - **สูตร:** `Stop Loss = ราคาปัจจุบัน - (ATR * Multiplier)`
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro + ATR")
    
    # --- 3. Sidebar ---
    st.sidebar.header("💰 Portfolio Settings")
    p_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    r_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    atr_mult = st.sidebar.slider("ATR Multiplier:", 1.0, 3.0, 1.5)
    
    st.sidebar.divider()
    assets = st.sidebar.multiselect("เลือกหุ้น:", 
                                    options=["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK", "PTT.BK", "CPALL.BK"], 
                                    default=["NVDA", "AAPL", "BTC-USD"])

    # --- 4. ฟังก์ชันดึงข้อมูล ---
    def get_data(ticker):
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(
