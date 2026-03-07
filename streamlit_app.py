import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; color: #ffffff; }
.risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ การทำงานของระบบ"])

with tab2:
    st.header("📖 กลไกการคุมความเสี่ยง (The 1% Rule)")
    st.markdown("ระบบคำนวณจำนวนหุ้นให้สัมพันธ์กับเงินต้น เพื่อให้คุณเสียไม่เกิน 1% ต่อการเทรดหนึ่งครั้ง")

with tab3:
    st.header("⚙️ System Internal")
    st.info("Logic: SMA200 Trend Filter + RSI Buy on Dip + Silver Volume Analysis")

# --- 3. ระบบหลัก ---
with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # Sidebar
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Assets")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้น:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK"])), default=default_assets)
    
    # ฟังก์ชันดึงข้อมูล (แก้ไข Syntax Error เรียบร้อย)
    def get_data(ticker, interval="1d", data_period="2y"):
        try:
            # รายชื่อหุ้นไทยเพื่อเติม .BK อัตโนมัติ
            thai_tickers = ["PT
