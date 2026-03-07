import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

# CSS ตกแต่ง
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบจัดการรายชื่อหุ้น (Session State) ---
# ใช้สำหรับเก็บรายชื่อหุ้นที่ผู้ใช้ เพิ่ม/ลบ
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = ["^GSPC", "NVDA", "AAPL", "BTC-USD", "PTT.BK"]

# --- 3. Sidebar: ส่วนควบคุม ---
st.sidebar.header("🛠️ จัดการรายการหุ้น")

# ส่วนที่ 1: เพิ่มหุ้น
with st.sidebar.expander("➕ เพิ่มหุ้น", expanded=True):
    new_stock = st.text_input("ชื่อ Ticker (เช่น TSLA):").upper().strip()
    if st.button("เพิ่มเข้าลิสต์"):
        if new_stock and new_stock not in st.session_state.stock_list:
            st.session_state.
