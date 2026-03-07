import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอและสไตล์ ---
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

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ ทำอย่างไรให้ "ห้ามพัง" (Zero Ruin)
    1. **Never Bet All:** อย่าลงเงินทั้งหมดในหุ้นตัวเดียว
    2. **The 1% Rule:** ในแต่ละการเทรด ถ้าผิดทาง คุณควรเสียเงินไม่เกิน **1% ของเงินต้นทั้งหมด**
    3. **Position Sizing:** ซื้อจำนวนหุ้นให้สัมพันธ์กับระยะห่างของจุด Stop Loss
    """)
    st.info("💡 สูตร: จำนวนหุ้น = (เงินทุนทั้งหมด x %ความเสี่ยง) / (ราคาซื้อ - ราคา Stop Loss)")

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # --- 3. Sidebar: การตั้งค่าพอร์ตและหุ้น ---
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท
