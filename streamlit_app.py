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

st.title("🛡️ Safe Heaven Scanner (Pro Mode)")

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

# รวมรายชื่อหุ้น
assets_to_scan = []
for group in selected_presets:
    assets_to_scan.extend(preset_options[group])

manual_assets = st.sidebar.text_input("เพิ่มชื่อหุ้นเอง (เช่น PTT.BK, TSLA):", "")
if manual_assets:
    assets_to_scan.extend([x.strip().upper() for x in manual_assets.split(",")])

# --- 3. ฟังก์ชันคำนวณ ---
def calculate_indicators(df):
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=60)
def fetch_data(tickers):
    results = []
    for ticker in tickers:
        try:
            # ดึงข้อมูลรายวัน ย้อนหลัง 2 ปี
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 200:
                continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-
