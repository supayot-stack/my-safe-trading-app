import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

# --- 2. ระบบหน่วยความจำ Watchlist ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "AAPL"]

# --- 3. ฟังก์ชันดึงข้อมูลและคำนวณ Indicator ---
@st.cache_data(ttl=300)
def fetch_stock_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # คำนวณ SMA 200 และ RSI
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        return df
    except: return None

# --- 4. ส่วนแสดงผลหลัก ---
st.title("""🛡️ Safe Heaven Quant Pro""")

# Sidebar สำหรับตั้งค่าหน่วยเวลา
st.sidebar.header("""⚙️ Settings""")
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_label = st.sidebar.selectbox("""เลือกหน่วยเวลา:""", list(itv_map.keys()))
itv_code = itv_map[itv_label]

# ตารางสแกนสัญญาณ
st.subheader(f"""🎯 สแกนสัญญาณเทคนิค ({itv_label})""")
results = []
for t in st.session_state.my_watchlist:
    d = fetch_stock_data(t, itv_code)
    if d is not None:
        last = d.iloc[-1]
