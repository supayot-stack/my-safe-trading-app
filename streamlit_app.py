import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

# --- 2. ระบบ Watchlist (คงหุ้น Top 5 ไว้เป็นหลัก) ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "NVDA", "AAPL", "BTC-USD"]

# --- 3. ฟังก์ชันดึงข้อมูล (Universal Fetch) ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: 
            return None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        return df
    except: 
        return None

# --- 4. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["Scanner", "Manual"])

with tab2:
    st.header("""📖 คู่มือการใช้งาน""")
    st.info("""ระบบใช้ SMA 200 ดูแนวโน้ม และ RSI ดูแรงซื้อขาย""")
    st.write("""1. ตารางจะแสดงสัญญาณ BUY เมื่อราคาอยู่เหนือเส้น 200 วันและ RSI ต่ำกว่า 40""")
    st.write("""2. คุณสามารถพิมพ์ชื่อหุ้นใหม่ๆ เพิ่มเข้าไปในรายการได้เอง""")

with tab1:
    st.title("""🛡️ Safe Heaven Quant Scanner""")

    # --- ส่วนที่เพิ่มเข้ามา: ปุ่มเพิ่มหุ้น (Add Stock) ---
    with st.expander("""➕ เพิ่มหุ้นตัวอื่นๆ เข้าสู่ระบบสแกน"""):
        c1, c2 = st.columns([3, 1])
        with c1:
            new_ticker = st.text_input("""ระบุชื่อย่อหุ้น (เช่น CPALL.BK, TSLA, ETH-USD):""").upper().strip()
        with c2:
            st.write(""" """)
            if st.button("""เพิ่มหุ้น"""):
                if new_ticker:
                    with st.spinner("""กำลังตรวจสอบข้อมูล..."""):
                        check = fetch_data(new_ticker, "1d")
                        if check is not None:
                            if new_ticker not in st.session_state.my_watchlist:
                                st.session_state.my_watchlist.append(new_ticker)
                                st.rerun
