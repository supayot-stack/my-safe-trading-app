import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

# --- 2. ระบบหน่วยความจำ Watchlist ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "TSLA", "AAPL"]

# --- 3. ฟังก์ชันดึงข้อมูลและคำนวณ Indicator ครบวงจร ---
@st.cache_data(ttl=300)
def fetch_full_data(ticker, interval):
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
        
        # กลยุทธ์ 2: Relative Volume (RVOL)
        df['Vol_Avg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_Avg']
        
        # กลยุทธ์ 3: Bollinger Squeeze
        df['MA20'] = df['Close'].rolling(20).mean()
        df['StdDev'] = df['Close'].rolling(20).std()
        df['Upper_BB'] = df['MA20'] + (2 * df['StdDev'])
        df['Lower_BB'] = df['MA20'] - (2 * df['StdDev'])
        
        # Keltner Channel (Simplified)
        df['TR'] = np.maximum(df['High'] - df['Low'], 
                   np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                   abs(df['Low'] - df['Close'].shift(1))))
        df['ATR'] = df['TR'].rolling(20).mean()
        df['Upper_KC'] = df['MA20'] + (1.5 * df['ATR'])
        df['Lower_KC'] = df['MA20'] - (1.5 * df['ATR'])
        
        # Squeeze Logic: BB อยู่ใน KC
        df['Squeeze'] = (df['Lower_BB'] > df['Lower_KC']) & (df['Upper_BB'] < df['Upper_KC'])
        
        return df
    except: return None

# --- 4. การสร้าง Tabs แยกตามหน้ากลยุทธ์ ---
tab_main, tab_vol, tab_sqz, tab_man = st.tabs([
    "🛡️ SMA & RSI (Trend)", 
    "📊 Volume Hunter (RVOL)", 
    "🚀 Squeeze (Breakout)", 
    "📖 Technique Manual"
])

# Sidebar Settings
st.sidebar.header("""Global Settings""")
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_label = st.sidebar.selectbox("""หน่วยเวลาหลัก:""", list(itv_map.keys()))
itv_code = itv_map[itv_label]

# --- ห้องที่ 1: SMA & RSI (คงเดิมจาก main1) ---
with tab_main:
    st.title("""🛡️ Trend Follower (SMA 200 + RSI)""")
    results = []
    for t in st.session_state.my_watchlist:
        d = fetch_full_data(t, itv_code)
        if d is not None:
            last = d.iloc[-1]
            p, r, s = last['Close'], last['RSI'], last['SMA200']
            sig = "🟢 BUY" if p > s and r < 40 else "🔴 EXIT" if p < s else "WAIT"
            results.append({"Ticker": t, "Price": f"{p:,.2f}", "RSI": round(r,1), "Signal": sig})
    st.table(pd.DataFrame(results))

# --- ห้องที่ 2: Volume Hunter (ใหม่!) ---
with tab_vol:
    st.title("""📊 Volume Hunter (Relative Volume)""")
    st.write("""สแกนหาหุ้นที่มีวอลุ่มเข้าผิดปกติเมื่อเทียบกับค่าเฉลี่ย 20 วัน""")
    vol_results = []
    for t in st.session_state.my_watchlist:
        d = fetch_full_data(t, itv_code)
        if d is not None:
            last = d.iloc[-1]
            rvol = last['RVOL']
            status = "🔥 HIGH VOL" if rvol > 2 else "Normal"
            vol_results.append({"Ticker": t, "Current Vol": f"{last['Volume']:,.0f}", "RVOL": round(rvol, 2), "Status": status})
    st.dataframe(pd.DataFrame(vol_results), use_container_width=True)

# --- ห้องที่ 3: Squeeze Breakout (ใหม่!) ---
with tab_sqz:
    st.title("""🚀 Volatility Squeeze""")
    st.write("""สแกนหาหุ้นที่ราคากำลังบีบตัวนิ่ง และเตรียมเลือกทางระเบิด""")
    sqz_results = []
    for t in st.session_state.my_watchlist:
        d = fetch_full_data(t, itv_code)
        if d is not None:
            last = d.iloc[-1]
            is_sqz = "💎 SQUEEZING" if last['Squeeze'] else "Released"
            sqz_results.append({"Ticker": t, "Price": f"{last['Close']:,.2f}", "Squeeze Status": is_sqz})
    st.table(pd.DataFrame(sqz_results))

# --- ห้องที่ 4: คู่มือแยกเทคนิค (ใหม่!) ---
with tab_man:
    st
