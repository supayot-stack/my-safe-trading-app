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
    .stButton>button { width: 100%; border-radius: 5px; background-color: #262730; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบจัดการรายชื่อหุ้น (Session State) ---
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = ["^GSPC", "NVDA", "AAPL", "BTC-USD", "PTT.BK"]

# --- 3. Sidebar: จัดการรายชื่อหุ้น ---
st.sidebar.header("🛠️ Asset Management")

# ส่วนเพิ่มหุ้น
with st.sidebar.expander("➕ เพิ่มหุ้น", expanded=True):
    new_ticker = st.text_input("พิมพ์ชื่อ Ticker:").upper().strip()
    if st.button("เพิ่มเข้าลิสต์"):
        if new_ticker and new_ticker not in st.session_state.stock_list:
            st.session_state.stock_list.append(new_ticker)
            st.rerun()

# ส่วนลบหุ้น
with st.sidebar.expander("🗑️ ลบหุ้น"):
    if st.session_state.stock_list:
        to_delete = st.selectbox("เลือกหุ้นที่จะลบ:", st.session_state.stock_list)
        if st.button("ลบออก"):
            st.session_state.stock_list.remove(to_delete)
            st.rerun()
    else:
        st.write("ไม่มีหุ้นในรายการ")

st.sidebar.divider()
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "
