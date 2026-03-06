import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>", unsafe_allow_html=True)

# --- 2. ระบบหน่วยความจำ Watchlist ---
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA"]

# --- 3. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงานอย่างละเอียด"])

# --- TAB 2: คู่มือ (คงไว้ครบตาม main) ---
with tab2:
    st.header("📖 คู่มือการใช้งาน Safe Heaven Scanner")
    st.subheader("🏗️ 1. การนำเข้าข้อมูล")
    st.info("ดึงข้อมูลจาก Yahoo Finance ย้อนหลัง 2 ปี เพื่อคำนวณ SMA 200 วัน")
    st.subheader("🧬 2. ตัวชี้วัด")
    st.write("- **SMA 200:** ดูเทรนด์หลัก (ราคาเหนือเส้น = ขาขึ้น)")
    st.write("- **RSI 14:** ดูจุดซื้อขาย (ต่ำกว่า 40 = ถูก / สูงกว่า 75 = แพง)")
    st.subheader("🎯 3. ตรรกะการสแกน")
    st.success("🟢 STRONG BUY: ราคา > SMA 200 และ RSI < 40")
    st.subheader("🚀 4. ขั้นตอนการใช้งาน")
    st.markdown("1. เพิ่มหุ้นที่สนใจ 2. ดูสัญญาณในตาราง 3. ตรวจสอบกราฟเพื่อยืนยัน")

# --- TAB 1: ระบบหลัก ---
with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")

    # --- ส่วนจัดการหุ้น (Watchlist Management) ---
    with st.expander("🛠️ จัดการรายชื่อหุ้น (เพิ่ม/ลด หุ้นใน Watchlist)"):
        # ส่วนเพิ่มหุ้น
        col_in, col_add = st.columns([3, 1])
        with col_in:
            new_ticker = st.text_input("ระบุชื่อหุ้นที่ต้องการเพิ่ม (เช่น CPALL.BK, TSLA, BTC-USD):").upper().strip()
        with col_add:
            st.write(" ")
            if st.button("➕ เพิ่มหุ้น"):
                if new_ticker and new_ticker not in st.session_state.my_watchlist:
                    st.session_state.my_watchlist.append(new_ticker)
                    st.rerun()
        
        st.divider()
        
        # ส่วนลบหุ้น (แบบรายตัว)
        st.write("📋 รายการหุ้นปัจจุบัน (กดปุ่ม ❌ เพื่อลบออก)")
        if st.session_state.my_watchlist:
            # สร้างแถวสำหรับการลบหุ้น
            for i, ticker in enumerate(st.session_state.my_watchlist):
                col_name, col_del = st.columns([5, 1])
                col_name.write(f"🔹 {ticker}")
                if col_del.button("❌ ลบ", key=f"del_{ticker}"):
                    st.session_state.my_watchlist.remove(ticker)
                    st.rerun()
        else:
            st.info("ยังไม่มีหุ้นในรายการ")

    # Sidebar Settings
    st.sidebar.header("Settings")
    itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
    itv_label = st.sidebar.selectbox("หน่วยเวลา:", list(itv_map.keys()))
    itv_code = itv_map[itv_label]

    # ฟังก์ชันดึงข้อมูล
    @st.cache_data(ttl=300)
    def fetch_data(ticker, interval):
        try:
            p = "2y" if interval == "1d" else "60d"
            df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            return df
        except: return None

    # แสดงตารางสแกน
    st.subheader(f"🎯 ผลการสแกนสัญญาณ ({itv_label})")
    scan_results = []
    for t in st.session_state.my_watchlist:
        d = fetch_data(t, itv_code)
        if d is not None:
            last = d.iloc[-1]
            p, r, s = last['Close'], last['RSI'], last['SMA200']
            if p > s and r < 40: sig = "🟢 STRONG BUY"
            elif r > 75: sig = "💰 PROFIT"
            elif p < s: sig = "🔴 EXIT"
            else: sig = "WAIT"
            scan_results.append({"หุ้น": t, "ราคา": f"{p:,.2f}", "RSI": round(r,1), "สัญญาณ": sig})
    
    if scan_results:
        st.dataframe(pd.DataFrame(scan_results), use_container_width=True, hide_index=True)
    else:
        st.info("กรุณาเพิ่มชื่อหุ้น หรือรอข้อมูลให้ครบ 200 แท่ง")

    st.divider()
    
    # ส่วนแสดงกราฟ
    if st.session_state.my_watchlist:
        selected = st.selectbox("🔍 วิเคราะห์กราฟรายตัว:", st.session_state.my_watchlist)
        plot_df = fetch_data(selected, itv_code)
        
        if plot_df is not None:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)
