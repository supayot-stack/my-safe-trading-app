import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Classic", layout="wide")

# CSS: เน้นตัวเลขใหญ่ๆ และพื้นหลังสะอาด
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    h1 { color: #1e222d; font-family: sans-serif; }
    .status-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner")

# --- 2. ตั้งค่าหุ้น (จัดกลุ่มแบบเรียบง่าย) ---
assets = {
    "🇺🇸 USA/Global": ["^GSPC", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"],
    "🇹🇭 Thai Market": ["^SET50.BK", "PTT.BK", "AOT.BK", "SCB.BK", "KBANK.BK"],
    "₿ Crypto": ["BTC-USD", "ETH-USD"]
}

# รวมหุ้นทั้งหมด
all_list = []
for v in assets.values(): all_list.extend(v)

st.sidebar.header("⏱️ เลือกหน่วยเวลา")
itv = st.sidebar.selectbox("หน่วยเวลา:", ["1 วัน", "1 ชั่วโมง", "5 นาที"], index=0)
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}

# --- 3. ฟังก์ชันคำนวณ ---
def get_data(ticker, interval):
    period = "2y" if interval == "1d" else "60d"
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if df.empty or len(df) < 200: return None
    
    # SMA 200 & RSI 14
    df['SMA200'] = df['Close'].rolling(200).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    return df

# --- 4. แสดงผล Dashboard ---
st.subheader(f"📈 สรุปสัญญาณล่าสุด ({itv})")
cols = st.columns(4)
summary_data = []

# ดึงข้อมูลมาโชว์ 4 ตัวหลัก (ดัชนีและบิทคอยน์)
main_picks = ["^GSPC", "^SET50.BK", "BTC-USD", "
