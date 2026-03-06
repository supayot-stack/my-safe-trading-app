import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. การตั้งค่าหน้าจอ (สไตล์ main1) ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

# --- 2. ระบบหน่วยความจำ Watchlist ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "AAPL"]

# --- 3. ฟังก์ชันดึงข้อมูลแบบ All-in-One (Support ทุกเทคนิค) ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # กลยุทธ์ 1: SMA + RSI
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # กลยุทธ์ 2: RVOL
        df['Vol_Avg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / (df['Vol_Avg'] + 1e-9)
        
        # กลยุทธ์ 3: Squeeze
        df['MA20'] = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['Upper_BB'] = df['MA20'] + (2 * std)
        df['Lower_BB'] = df['MA20'] - (2 * std)
        tr = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
        atr = tr.rolling(20).mean()
        df['Upper_KC'] = df['MA20'] + (1.5 * atr)
        df['Lower_KC'] = df['MA20'] - (1.5 * atr)
        df['Squeeze'] = (df['Lower_BB'] > df['Lower_KC']) & (df['Upper_BB'] < df['Upper_KC'])
        
        return df
    except: return None

# --- 4. Sidebar: โหมดและหน่วยเวลา ---
st.sidebar.header("""⚙️ Control Center""")
mode = st.sidebar.radio("""🎯 เลือกเทคนิคการเทรด:""", [
    "Trend Follower (SMA+RSI)", 
    "Volume Hunter (RVOL)", 
    "Volatility Squeeze (Breakout)"
])

itv_label = st.sidebar.selectbox("""⏱️ หน่วยเวลา:""", ["1 วัน", "1 ชั่วโมง", "5 นาที"])
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_code = itv_map[itv_label]

# --- 5. การแสดงผลเนื้อหาแยกตามเทคนิค (รูปแบบตารางเหมือน main1) ---

st.title(f"""🛡️ {mode} Mode""")

if mode == "Trend Follower (SMA+RSI)":
    st.info("""📖 [Manual] เน้นถือยาวตามเทรนด์ใหญ่ ราคาต้องยืนเหนือ SMA 200 และซื้อเมื่อ RSI ย่อตัวลงต่ำกว่า 40""")
    st.subheader(f"""🎯 ผลการสแกนสัญญาณ ({itv_label})""")
    results = []
    for t in st.session_state.my_watchlist:
        d = fetch_data(t, itv_code)
        if d is not None:
            l = d.iloc[-1]
            p, r, s = l['Close'], l['RSI'], l['SMA200']
            sig = """🟢 STRONG BUY""" if p > s and r < 40 else """💰 PROFIT""" if r >
