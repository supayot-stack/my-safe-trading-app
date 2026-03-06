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
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 15px; 
        border: 1px solid #30363d; 
    }
    h2, h3 { color: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบจัดการหุ้น (Session State) ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA"]

# --- 3. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงาน"])

with tab2:
    st.header("📖 คู่มือการใช้งานระบบ")
    
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🏗️ 1. ข้อมูล (Data)")
        st.write("ดึงข้อมูลราคาจาก Yahoo Finance ย้อนหลัง 2 ปี พร้อมปรับราคาปันผลอัตโนมัติ")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🧬 2. ตัวชี้วัด (Indicators)")
        st.write("ใช้ SMA 200 วันดูแนวโน้ม และใช้ RSI 14 วันดูแรงเหวี่ยงของราคา")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div
