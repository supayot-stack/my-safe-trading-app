import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>", unsafe_allow_html=True)

# --- 2. ระบบ Watchlist (Top 5) ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "NVDA", "AAPL", "BTC-USD"]

# --- 3. ฟังก์ชันดึงข้อมูล ---
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
    st.header("How to use")
    # ใช้ triple quotes เพื่อความเสถียรของ string
    st.write("""1. ระบบจะสแกนหุ้น Top 5 ให้อัตโนมัติ""")
    st.write("""2. สามารถเพิ่มหุ้นตัวอื่นได้ที่ช่อง Add Stock""")
    st.write("""3. SMA 200 คือเส้นแนวโน้มหลัก / RSI คือแรงเหวี่ยงราคา""")

with tab1:
    st.title("🛡️ Safe Heaven Quant")

    # --- ส่วนเพิ่มหุ้นนอกรายการ ---
    with st.expander("➕ Add Stock (Ticker Symbol)"):
        col1, col2 = st.columns([3, 1])
        with col1:
            # รับชื่อหุ้น และล้างช่องว่างออก
            new_ticker = st.text_input("Example: CPALL.BK, TSLA, BTC-USD").upper().strip()
        with col2:
            st.write(" ")
            if st.button("Add"):
                if new_ticker:
                    check = fetch_data(new_ticker, "1d")
                    if check is not None:
