import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ (คงเดิม) ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .ai-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันเสริมสำหรับ Backtest (เพิ่มใหม่เพื่อความโปร) ---
def run_backtest_logic(df, initial_cap):
    df['Sig'] = (df['Close'] > df['SMA200']) & (df['RSI'] < 45)
    capital = initial_cap
    equity_curve = [initial_cap]
    trades = []
    
    in_pos = False
    for i in range(1, len(df)):
        if not in_pos and df['Sig'].iloc[i]:
            entry = df['Close'].iloc[i]
            sl = df['SL'].iloc[i]
            tp = df['TP'].iloc[i]
            in_pos = True
        elif in_pos:
            curr = df['Close'].iloc[i]
            if curr <= sl or curr >= tp:
                ret = (curr / entry) - 1
                capital *= (1 + ret)
                trades.append(ret)
                in_pos = False
        equity_curve.append(capital)
    
    win_rate = (len([r for r in trades if r > 0]) / len(trades) * 100) if trades else 0
    pf = abs(sum([r for r in trades if r > 0]) / (sum([r for r in trades if r < 0]) + 1e-9)) if trades else 0
    mdd = (pd.Series(equity_curve) / pd.Series(equity_curve).cummax() - 1).min() * 100
    return win_rate, pf, mdd, equity_curve

# --- 3. ส่วนเมนู (คงเดิม) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ ทำอย่างไรให้ "ห้ามพัง" (Zero Ruin)
    1. **The 1% Rule:** เสียเงินไม่เกิน 1% ของเงินต้นต่อการเทรด
    2. **ATR Stop Loss:** ใช้ความผันผวนจริงกำหนดจุดหนี (ไม่ใช่สุ่มเดา %)
    3. **Correlation:** อย่าซื้อหุ้นที่วิ่งเหมือนกันพร้อมกันทั้งหมด
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + Elite Analytics")
    
    # --- 4. Sidebar (คงเดิม) ---
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK", "GC=F"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list: final_list.append(custom_ticker)

    # --- 5. ฟังก์ชันดึงข้อมูล (Upgrade RSI/ATR/Caching) ---
    @st.cache_data(ttl=3600)
    def get_data(ticker):
        try:
            df = yf.download(ticker, period="2y", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(
