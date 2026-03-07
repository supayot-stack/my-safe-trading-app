import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING & STYLE ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { 
        background-color: #2c3333; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 6px solid #ff4b4b; 
        margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ กลไกการคุมความเสี่ยง (The 1% Rule)
    หัวใจสำคัญคือ **"ขาดทุนได้ แต่ห้ามพัง"**
    * **Risk Per Trade:** กำหนดว่าถ้าผิดทาง จะยอมเสียเงินไม่เกินกี่บาท (เช่น 1% ของพอร์ต)
    * **Position Sizing:** ซื้อจำนวนหุ้นให้สัมพันธ์กับจุด Stop Loss
    """)
    st.info("💡 สูตร: จำนวนหุ้น = (
