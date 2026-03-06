import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>", unsafe_allow_html=True)

# --- 2. ระบบหน่วยความจำ Watchlist (ใช้เก็บหุ้นที่ดึงเพิ่มเข้ามา) ---
if 'my_watchlist' not in st.session_state:
    # รายการเริ่มต้น (Preset)
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA"]

# --- 3. ฟังก์ชันดึงข้อมูล (หัวใจหลักที่ใช้ดึงหุ้นตัวไหนก็ได้) ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        # ดึงข้อมูลจาก Yahoo Finance ตามชื่อ Ticker ที่ส่งเข้าไป
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: 
            return None
        
        # จัดการชื่อ Column กรณีเป็น MultiIndex
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
            
        # คำนวณค่าทางเทคนิค
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
    st.header("📖 วิธีใช้งานระบบดึงข้อมูลหุ้น")
    st.info("คุณสามารถนำชื่อย่อหุ้นจาก Yahoo Finance มาใส่เพื่อดึงข้อมูลได้ทันที")
    st.write("1. **หุ้นไทย:** เติม .BK (เช่น CPALL.BK, AOT.BK)")
    st.write("2. **หุ้นเมกา:** ใส่ชื่อย่อได้เลย (เช่น TSLA, META, GOOG)")
    st.write("3. **คริปโต:** เติม -USD (เช่น ETH-USD, DOGE-USD)")

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")

    # --- ส่วนที่ดึงหุ้นใหม่เข้ามา (Dynamic Ingestion) ---
    st.subheader("➕ ดึงข้อมูลหุ้นตัวใหม่เข้าสู่ระบบ")
    c1, c2 = st.columns([3, 1])
    with c1:
        # ช่องรับชื่อหุ้นตัวไหนก็ได้ในโลก
        target_ticker = st.text_input("พิมพ์ชื่อย่อหุ้น (Ticker Symbol):", placeholder="เช่น CPALL.BK หรือ TSLA").upper().strip()
    with c2:
        st.write(" ")
        if st.button("ดึงข้อมูลและเพิ่มเข้าตาราง"):
            if target_ticker:
                with st.spinner(f"กำลังดึงข้อมูล {target_ticker}..."):
                    check_data = fetch_data(target_ticker, "1d") # เช็คว่ามีหุ้นนี้จริงไหม
                    if check_data is not None:
                        if target_ticker not in st.session_state.my_watchlist:
                            st.session_state.my_watchlist.append(target_ticker)
                            st.success(f"ดึงข้อมูล {target_ticker} สำเร็จ!")
                            st.rerun()
                        else:
                            st.warning("หุ้นตัวนี้อยู่ในรายการอยู่แล้ว")
                    else:
                        st.error("ไม่พบข้อมูลหุ้นนี้ หรือข้อมูลไม่เพียงพอ (ต้องมีประวัติอย่างน้อย 200 วัน)")

    # Sidebar
    st.sidebar.header("Settings")
    itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
    itv_label = st.sidebar.selectbox("หน่วยเวลา:", list(itv_map.keys()))
    itv_code = itv_map[itv_label]

    # --- 5. แสดงตารางสแกน (รวมหุ้นทุกตัวที่ดึงมา) ---
    st.subheader(f"🎯 รายการวิเคราะห์ปัจจุบัน ({itv_label})")
    scan_results = []
    for t in st.session_state.my_watchlist:
        d = fetch_data(t, itv_code)
        if d is not None:
            last = d.iloc[-1]
            p, r, s = last['Close'], last['RSI'], last['SMA200']
            
            # ตรรกะตัดสินใจ
            if p > s and r < 40: sig = "🟢 STRONG BUY"
            elif r > 75: sig = "💰 PROFIT"
            elif p < s: sig = "🔴 EXIT"
            else: sig = "WAIT"
            
            scan_results.append({"หุ้น": t, "ราคา": f"{p:,.2f}", "RSI": round(r,1), "สัญญาณ": sig})
    
    if scan_results:
        df_display = pd.DataFrame(scan_results)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # ปุ่มลบหุ้นออกจากรายการวิเคราะห์
        col_del_1, col_del_2 = st.columns([1, 4])
        with col_del_1:
            if st.button("🗑️ ล้างรายการทั้งหมด"):
                st.session_state.my_watchlist = []
                st.rerun()
    
    st.divider()
    
    # --- 6. ส่วนแสดงกราฟ (ดึงข้อมูลตัวที่เลือกมาวาดกราฟละเอียด) ---
    if st.session_state.my_watchlist:
        selected = st.selectbox("🔍 เลือกดูรายละเอียดกราฟ:", st.session_state.my_watchlist)
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
