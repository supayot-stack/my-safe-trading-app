import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

# ปรับแต่งสีพื้นหลังแบบง่าย (ลดการใช้ HTML ซับซ้อนเพื่อเลี่ยง Error)
st.markdown("<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>", unsafe_allow_html=True)

# --- 2. ระบบจัดการหุ้น (Session State) ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA"]

# --- 3. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงาน"])

with tab2:
    st.header("📖 คู่มือการใช้งานระบบ")
    
    # ใช้ st.info หรือ st.help แทนการเขียน HTML Div เองเพื่อความชัวร์
    st.subheader("🏗️ 1. การดึงข้อมูล (Data)")
    st.info("ระบบใช้ข้อมูลจาก Yahoo Finance ย้อนหลัง 2 ปี เพื่อคำนวณเส้น SMA 200")

    st.subheader("🧬 2. ตัวชี้วัด (Indicators)")
    st.success("SMA 200 วัน: ดูแนวโน้มระยะยาว | RSI 14 วัน: ดูจุดซื้อขายที่ได้เปรียบ")

    st.subheader("🎯 3. กลยุทธ์ Safe Heaven")
