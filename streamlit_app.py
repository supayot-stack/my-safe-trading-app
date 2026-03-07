import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 20px; border-radius: 12px; border-left: 6px solid #00ffcc; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & ATR", "📖 คู่มือเทคนิค"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + ATR")

    # --- 3. Sidebar: Settings ---
    st.sidebar.header("💰 Portfolio Settings")
    p_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    atr_mult = st.sidebar.slider("ATR Multiplier (SL):", 1.0, 3.0, 1.5)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    # ส่วนของ List หุ้นแนะนำ
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกจากลิสต์:", options=list(set(default_assets + ["PTT.BK", "CPALL.BK", "AOT.BK"])), default=default_assets)
    
    # ส่วนของการเพิ่มหุ้นเอง (Ticker)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นเอง (เช่น PTT.BK, MSFT):").upper().strip()

    # รวม List หุ้นทั้งหมด
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    # --- 4. DATA ENGINE (Function) ---
    def get_market_data(ticker):
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # Indicators
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            
            # RSI
            delta = df['Close'].diff
