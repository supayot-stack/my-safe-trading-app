import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .guide-section { 
        background-color: #1e222d; 
        padding: 25px; 
        border-radius: 15px; 
        margin-bottom: 20px; 
        border: 1px solid #30363d; 
    }
    h2, h3 { color: #58a6ff; }
    .step-box {
        background-color: #262c3a;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00ffcc;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบจัดการหุ้นที่สนใจ (Custom Watchlist) ---
if 'my_watchlist' not in st.session_state:
    # ตั้งค่าเริ่มต้นเป็นหุ้นยอดนิยม
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "AAPL"]

# --- 3. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงานของระบบ"])

with tab2:
    st.header("📖 เจาะลึกการทำงานของ Safe Heaven Scanner")
    
    # คู่มือส่วนที่ 1-4 (ตามที่คุณเคยบันทึกไว้)
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🏗️ 1. ส่วนการนำเข้าข้อมูล (Data Fetching)")
        st.write("ส่วนนี้เปรียบเสมือน 'ท่อน้ำเลี้ยง' ของโปรแกรมครับ เราใช้ไลบรารี yfinance เพื่อดึงข้อมูลราคาหุ้นจาก Yahoo Finance ทั่วโลก")
        st.markdown("* **Ticker:** คือชื่อย่อหุ้น\n* **Period & Interval:** ย
