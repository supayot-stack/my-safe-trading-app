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
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนจัดการรายชื่อหุ้น (Add/Remove) ---
st.sidebar.header("🔍 Asset Management")

# รายการหุ้นเริ่มต้น
default_stocks = ["^GSPC", "^SET50.BK", "NVDA", "AAPL", "TSLA", "BTC-USD", "ETH-USD", "PTT.BK"]

# ใช้ Session State เพื่อเก็บรายการหุ้นที่ผู้ใช้แก้ไข
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = default_stocks

# ช่องสำหรับพิมพ์ชื่อหุ้นเพิ่ม (เช่น MSFT, CPALL.BK)
new_stock = st.sidebar.text_input("➕ เพิ่มหุ้น (พิมพ์ Ticker):").upper()
if st.sidebar.button("Add to List"):
    if flag := new_stock and new_stock not in st.session_state.stock_list:
        st.session_state.stock_list.append(new_stock)
        st.rerun()

# ช่องสำหรับเลือกเอาหุ้นออก
stocks_to_show = st.sidebar.multiselect(
    "📝 รายการหุ้นที่สแกน:", 
    options=st.session_state.stock_list, 
    default=st.session_state.stock_list
)

st.sidebar.divider()
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv = st.sidebar.selectbox("⏱️ หน่วยเวลา:", list(itv_map.keys()), index=0)

# --- 3. ฟังก์ชันคำนวณ ---
@st.cache_data(ttl=300) # เพิ่ม Cache เพื่อความเร็ว
def get_data(ticker, interval):
    try:
        df = yf.download(ticker, period="2y" if interval=="1d" else "60d", interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        return df
    except: return None

# --- 4. ส่วนแสดงผล ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการใช้งาน"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")
    
    results = []
    with st.spinner('กำลังวิเคราะห์ข้อมูล...'):
        for t in stocks_to_show:
            df = get_data(t, itv_map[itv])
            if df is not None:
                last = df.iloc[-1]
                p, r, s = last['Close'], last['RSI'], last['SMA200
