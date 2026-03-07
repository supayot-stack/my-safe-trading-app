import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING ---
st.set_page_config(page_title="Safe Heaven Quant Pro ATR", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & ATR", "📖 คู่มือเทคนิค"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro + ATR")
    
    # --- 3. Sidebar: Settings & Asset Management ---
    st.sidebar.header("💰 Portfolio Settings")
    p_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    r_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    atr_mult = st.sidebar.slider("ATR Multiplier:", 1.0, 3.0, 1.5)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นจากลิสต์:", 
                                            options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK"])), 
                                            default=default_assets)
    
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ (เช่น PTT.BK):").upper().strip()
    
    # รวมรายชื่อหุ้น
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    # --- 4. ฟังก์ชันดึงข้อมูล ---
