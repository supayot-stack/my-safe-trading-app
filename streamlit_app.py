import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1e222d; border-radius: 5px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการใช้งานสำหรับมือใหม่"])

with tab2:
    st.header("📖 คู่มือการใช้งาน Safe Heaven Scanner")
    st.markdown("""
    ### 🛡️ กลยุทธ์ Safe Heaven
    เน้นการ **"ซื้อเมื่อย่อในขาขึ้น"** (Buy on Dip) โดยมีเงื่อนไขดังนี้:
    1. **SMA 200:** ราคาต้องยืนเหนือเส้นนี้เพื่อยืนยันว่าเป็นขาขึ้นระยะยาว
    2. **RSI 14:** ต้องต่ำกว่า 40 เพื่อหาจังหวะที่ราคา "ย่อตัว" มากพอให้เข้าซื้อ
    
    ---
    ### 🚦 วิธีอ่านสัญญาณ (Trading Signals)
    * 🟢 **STRONG BUY:** ราคา > SMA 200 **และ** RSI < 40 (จุดซื้อได้เปรียบ)
    * 💰 **PROFIT:** RSI > 75 (ราคาตึงเกินไป ควรเริ่มขายทำกำไร)
    * 🔴 **EXIT/AVOID:** ราคา < SMA 200 (ขาลง อันตราย ห้ามถือ)
    * ⚪ **WAIT:** ยังไม่เข้าเงื่อนไขใดๆ ให้ถือเงินสดรอ
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")

    # --- 3. ส่วน Sidebar: การจัดการหุ้น (Asset Management) ---
    st.sidebar.header("🔍 Asset Management")
    
    # หุ้นแนะนำเริ่มต้น (Top 5)
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    
    # ส่วนเลือก/ลบหุ้น
    selected_assets = st.sidebar.multiselect(
        "เลือกหุ้นจากรายการแนะนำ:",
        options=list(set(default_assets + ["MSFT", "GOOGL", "ETH-USD", "PTT.BK", "CPALL.BK", "GC=F"])),
        default=default_assets
    )

    # ส่วนเพิ่มหุ้นเอง
    custom_ticker = st.sidebar.text_input("➕ เพิ่มชื่อหุ้นอื่นๆ (เช่น META, OR.BK):").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    st.sidebar.divider()
    
    # --- 4. ส่วน Sidebar: การตั้งค่าหน่วยเวลา (Timeframe Settings) ---
    st.sidebar.header("⏱️ Timeframe Settings")
    
    itv_options = {
        "1 วัน (Investment)": {"iv": "1d", "period": "2y", "desc": "เน้นถือยาว/ออมหุ้น (แม่นยำ
