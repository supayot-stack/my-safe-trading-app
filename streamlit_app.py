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

# --- 2. ฟังก์ชันเสริมสำหรับ Backtest (แก้ไขจุด Error Profit Factor) ---
def run_backtest_logic(df, initial_cap):
    if df is None or len(df) < 20: return 0, 0, 0, [initial_cap]
    
    # กลยุทธ์: ซื้อเมื่อราคา > SMA200 และ RSI < 45
    df['Sig'] = (df['Close'] > df['SMA200']) & (df['RSI'] < 45)
    capital = initial_cap
    equity_curve = [initial_cap]
    trades = []
    
    in_pos = False
    entry, sl, tp = 0, 0, 0
    
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
    
    # คำนวณ Metrics (ปิดวงเล็บให้สมบูรณ์แล้ว)
    win_rate = (len([r for r in trades if r > 0]) / len(trades) * 100) if trades else 0
    
    pos_sum = sum([r for r in trades if r > 0])
    neg_sum = abs(sum([r for r in trades if r < 0]))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else (pos_sum if pos_sum > 0 else 0)
    
    mdd = (pd.Series(equity_curve) / pd.Series(equity_curve).cummax() - 1).min() * 100
    return win_rate, pf, mdd, equity_curve

# --- 3. ส่วนเมนู (คงเดิม) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% และระบบ Elite Quant")
    st.markdown("""
    ### 🛡️ ทำอย่างไรให้ "ห้ามพัง" (Zero Ruin)
    1. **The 1% Rule:** เสียเงินไม่เกิน 1% ของเงินต้นต่อหนึ่งการเทรด
    2. **Backtest:** ตรวจสอบสถิติย้อนหลังเพื่อให้มั่นใจในระบบ
    3. **Correlation:** หลีกเลี่ยงการซื้อสินทรัพย์ที่วิ่งตามกันมากเกินไป
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
    selected_assets = st.sidebar.multiselect("เลือกหุ้น:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK", "GC=F"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list: final_list.append(custom_ticker)

    # --- 5. ฟังก์ชันดึงข้อมูล (แก้ไขจุด Error MultiIndex) ---
    @st.cache_data(ttl=3600)
    def get_data(ticker):
        try:
            df = yf.download(ticker, period="2y", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            
            # ปิดวงเล็บให้สมบูรณ์แล้ว
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
            loss = -delta.where(delta < 0, 0).ewm(alpha=1/14, min_periods=14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            
            tr = pd.concat([(df['High']
