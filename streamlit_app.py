import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

# CSS ตกแต่งเมนูคู่มือ
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .guide-section { background-color: #1e222d; padding: 25px; border-radius: 15px; margin-bottom: 20px; border: 1px solid #30363d; }
    .logic-card { background-color: #262c3a; padding: 15px; border-radius: 10px; border-left: 5px solid #58a6ff; margin-top: 10px; }
    h2, h3 { color: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงานของระบบ"])

with tab2:
    st.header("📖 เจาะลึกการทำงานของ Safe Heaven Scanner")
    
    # ส่วนที่ 1: การนำเข้าข้อมูล
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🏗️ 1. ส่วนการนำเข้าข้อมูล (Data Fetching)")
        st.write("ส่วนนี้เปรียบเสมือน **'ท่อน้ำเลี้ยง'** ของโปรแกรม โดยดึงข้อมูลราคาหุ้นสดๆ จาก Yahoo Finance ทั่วโลก")
        st.markdown("""
        * **Ticker:** ชื่อย่อหุ้นที่คุณเลือก (เช่น BTC-USD, PTT.BK)
        * **Period & Interval:** ดึงข้อมูลย้อนหลัง 2 ปีเพื่อให้เพียงพอต่อการคำนวณเส้นค่าเฉลี่ย 200 วัน
        * **Auto Adjust:** ปรับราคาปันผลและแตกหุ้นให้อัตโนมัติ เพื่อให้ได้ราคาที่แม่นยำที่สุด
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ส่วนที่ 2: สมองกล
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
