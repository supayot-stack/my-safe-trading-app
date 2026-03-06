import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Scanner Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner (Standard & Top Picks)")

# --- 2. แถบเมนูด้านข้าง ---
st.sidebar.header("🎯 เลือกกลุ่มสินทรัพย์")

preset_options = {
    "ดัชนีหลัก (Market Index)": ["^GSPC", "^SET50.BK", "GC=F"],
    "เทคโนโลยี (Tech Giants)": ["NVDA", "AAPL", "MSFT", "GOOGL", "TSLA"],
    "การเงิน & ธนาคาร (Finance)": ["JPM", "GS", "SCB.BK", "KBANK.BK"],
    "พลังงาน & ขนส่ง (Energy/Aviation)": ["PTT.BK", "AOT.BK", "XOM"],
}

selected_presets = st.sidebar.multiselect(
    "เลือกกลุ่มหุ้น:", 
    list(preset_options.keys()),
    default=["ดัชนีหลัก (Market Index)"]
)

# รวมรายชื่อหุ้น (ลบตัวซ้ำออก)
assets_to_scan = []
for group in selected_presets:
    assets_to_scan.extend(preset_options[group])

manual_assets = st.sidebar.text_input("เพิ่มชื่อหุ้นเอง (เช่น PTT.BK, TSLA):", "")
if manual_assets:
    assets_to_scan.extend([x.strip().upper() for x in manual_assets.split(",")])

assets_to_scan = list(dict.fromkeys(assets_to_scan))

# --- 3. ฟังก์ชันคำนวณ ---
def calculate_indicators(df):
    # SMA 200
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    
    # RSI (14) - แก้ไขจุดที่ Syntax Error ปิดวงเล็บให้ครบ
