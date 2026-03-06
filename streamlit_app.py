import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .guide-section { background-color: #1e222d; padding: 25px; border-radius: 15px; margin-bottom: 20px; border: 1px solid #30363d; }
    .step-box { background-color: #262c3a; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ระบบจัดการหุ้นที่สนใจ (Custom Watchlist) ---
# ใช้ session_state เพื่อเก็บรายชื่อหุ้นที่ผู้ใช้เพิ่มเอง
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["PTT.BK", "BTC-USD", "NVDA"] # ค่าเริ่มต้น

# --- 3. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงานของระบบ"])

with tab2:
    st.header("📖 เจาะลึกการทำงานของ Safe Heaven Scanner")
    # (ส่วนที่ 1-5 ตามที่คุณต้องการ บันทึกไว้ใน main)
    st.markdown('<div class="guide-section">... (เนื้อหาคู่มือส่วนที่ 1-5 ที่บันทึกไว้) ...</div>', unsafe_allow_html=True)

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")

    # --- ส่วนเพิ่มหุ้น (Add Custom Stock) ---
    with st.expander("➕ เพิ่มหุ้นที่คุณสนใจลงในรายการสแกน"):
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            new_ticker = st.text_input("ใส่ชื่อย่อหุ้น (เช่น CPALL.BK, TSLA, ETH-USD):").upper()
        with col_btn:
            st.write(" ") # สร้างที่ว่างให้ปุ่มตรงกัน
            if st.button("เพิ่มเข้า Watchlist"):
                if new_ticker and new_ticker not in st.session_state.my_watchlist:
                    st.session_state.my_watchlist.append(new_ticker)
                    st.success(f"เพิ่ม {new_ticker} เรียบร้อย!")
                elif new_ticker in st.session_state.my_watchlist:
                    st.warning("หุ้นตัวนี้มีอยู่ในรายการแล้ว")

    # --- การดึงข้อมูลและสแกน ---
    st.sidebar.header("⏱️ Settings")
    itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
    itv_label = st.sidebar.selectbox("เลือกหน่วยเวลา:", list(itv_map.keys()), index=0)
    itv_code = itv_map[itv_label]

    @st.cache_data(ttl=300)
    def fetch_quant_data(ticker, interval):
        try:
            p = "2y" if interval == "1d" else "60d"
            df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if len(df) < 200: return None
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            return df
        except: return None

    # สแกนหุ้นใน Watchlist
    st.subheader(f"🎯 รายการสแกนสัญญาณปัจจุบัน ({itv_label})")
    results = []
    for t in st.session_state.my_watchlist:
        data = fetch_quant_data(t, itv_code)
        if data is not None:
            l = data.iloc[-1]
            p, r, s = l['Close'], l['RSI'], l['SMA200']
            if p > s and r < 40: sig = "🟢 STRONG BUY"
            elif r > 75: sig = "💰 PROFIT"
            elif p < s: sig = "🔴 EXIT"
            else: sig = "WAIT"
            results.append({"หุ้น": t, "ราคา": f"{p:,.2f}", "RSI": round(r,1), "สัญญาณ": sig})
    
    if results:
        res_df = pd.DataFrame(results)
        st.dataframe(res_df, use_container_width=True, hide_index=True)
        
        # ปุ่มล้าง Watchlist
        if st.button("🗑️ ล้างรายการทั้งหมด"):
            st.session_state.my_watchlist = []
            st.rerun()
    else:
        st.info("ยังไม่มีหุ้นในรายการ กรุณาเพิ่มชื่อหุ้นที่ช่องด้านบน")

    st.divider()
    
    # --- ส่วนวิเคราะห์กราฟ ---
    if st.session_state.my_watchlist:
        selected_asset = st.selectbox("🔍 วิเคราะห์กราฟรายตัวจาก Watchlist ของคุณ:", st.session_state.my_watchlist)
        plot_df = fetch_quant_data(selected_asset, itv_code)
        
        if plot_df
