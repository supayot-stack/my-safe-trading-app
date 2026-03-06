import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>", unsafe_allow_html=True)

# --- 2. ระบบ Watchlist (ใส่หุ้น Top 5 กลับมาเป็นค่าเริ่มต้น) ---
if 'my_watchlist' not in st.session_state:
    # คืนค่าหุ้น Top 5 และตัวหลักๆ กลับมา
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "NVDA", "AAPL", "BTC-USD"]

# --- 3. ฟังก์ชันดึงข้อมูลแบบ Universal ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: 
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
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงาน"])

with tab2:
    st.header("📖 คู่มือการใช้งาน")
    st.info("ระบบจะแสดงหุ้น Top 5 เป็นค่าเริ่มต้น และคุณสามารถเพิ่มหุ้นตัวอื่นได้เอง")
    st.markdown("""
    * **SMA 200:** เส้นเหลือง (เหนือเส้น = ขาขึ้น)
    * **RSI:** เส้นฟ้า (ต่ำกว่า 40 = จุดซื้อ / สูงกว่า 75 = จุดขาย)
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")

    # --- ส่วนเพิ่มหุ้นนอกรายการ (ที่ทำเพิ่มไว้ให้) ---
    with st.expander("➕ ดึงข้อมูลหุ้นตัวอื่นๆ เพิ่มเติม"):
        c1, c2 = st.columns([3, 1])
        with c1:
            target_ticker = st.text_input("พิมพ์ชื่อย่อหุ้นที่ต้องการดึงข้อมูล:", placeholder="เช่น CPALL.BK, TSLA").upper().strip()
        with c2:
            st.write(" ")
            if st.button("ดึงข้อมูลและเพิ่มเข้าตาราง"):
                if target_ticker:
                    with st.spinner(f"กำลังดึงข้อมูล {target_ticker}..."):
                        check_data = fetch_data(target_ticker, "1d")
                        if check_data is not None:
                            if target_ticker not in st.session_state.my_watchlist:
                                st.session_state.my_watchlist.append(target_ticker)
                                st.success(f"เพิ่ม {target_ticker} สำเร็จ!")
                                st.rerun()
                        else:
                            st.error("ไม่พบข้อมูลหรือหุ้นนี้มีข้อมูลไม่ถึง 200 วัน")

    # Sidebar
    st.sidebar.header("Settings")
    itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
    itv_label = st.sidebar.selectbox("หน่วยเวลา:", list(itv_map.keys()))
    itv_code = itv_map[itv_label]

    # --- 5. แสดงตารางสแกน (รวมหุ้น Top 5 + หุ้นที่เพิ่มเอง) ---
    st.subheader(f"🎯 รายการวิเคราะห์ปัจจุบัน ({itv_label})")
    scan_results
