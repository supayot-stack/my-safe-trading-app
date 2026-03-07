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
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .delete-btn>button { background-color: #ff4b4b; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบจัดการรายชื่อหุ้น (Session State) ---
if 'stock_list' not in st.session_state:
    # ค่าเริ่มต้น
    st.session_state.stock_list = ["^GSPC", "NVDA", "AAPL", "BTC-USD", "PTT.BK"]

# --- 3. Sidebar: ส่วนควบคุมการ เพิ่ม/ลบ ---
st.sidebar.header("🛠️ จัดการรายการหุ้น")

# ส่วนที่ 1: เพิ่มหุ้น
with st.sidebar.expander("➕ เพิ่มหุ้นใหม่", expanded=True):
    new_stock = st.text_input("พิมพ์ชื่อ Ticker (เช่น TSLA, CPALL.BK):").upper().strip()
    if st.button("เพิ่มเข้าสู่ระบบ"):
        if new_stock and new_stock not in st.session_state.stock_list:
            st.session_state.stock_list.append(new_stock)
            st.rerun()
        elif new_stock in st.session_state.stock_list:
            st.warning("มีหุ้นตัวนี้อยู่ในรายการแล้ว")

# ส่วนที่ 2: ลบหุ้น
with st.sidebar.expander("🗑️ ลบหุ้นออก", expanded=False):
    stock_to_remove = st.selectbox("เลือกหุ้นที่จะลบ:", ["-- เลือก --"] + st.session_state.stock_list)
    if st.button("ลบหุ้นที่เลือก", key="del_btn"):
        if stock_to_remove != "-- เลือก --":
            st.session_state.stock_list.remove(stock_to_remove)
            st.rerun()
    
    st.divider()
    if st.button("💥 ล้างรายการทั้งหมด"):
        st.session_state.stock_list = []
        st.rerun()

st.sidebar.divider()
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv = st.sidebar.selectbox("⏱️ หน่วย
