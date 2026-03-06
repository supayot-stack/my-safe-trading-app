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
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA"]

# --- 3. ฟังก์ชันดึงข้อมูล (Backbone) ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        return df
    except: return None

# --- 4. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 Scanner", "📖 Manual"])

with tab2:
    st.header("""📖 คู่มือการใช้งาน""")
    st.info("""ระบบจะช่วยสแกนหุ้นจาก List ของคุณ และเปรียบเทียบกับสัญญาณ SMA 200 และ RSI""")

# --- TAB 1: ระบบหลัก ---
with tab1:
    st.title("""🛡️ Safe Heaven Quant Scanner""")

    # --- ส่วนที่เพิ่มใหม่: หุ้นน่าสนใจ (Suggested Stocks) ---
    st.subheader("""💡 หุ้นและดัชนีที่น่าสนใจ (Quick Add)""")
    
    suggested = {
        "Indices": ["^GSPC", "^IXIC", "^SET.BK"], 
        "Tech Stocks": ["AAPL", "TSLA", "MSFT", "GOOG"],
        "Crypto": ["ETH-USD", "SOL-USD", "DOGE-USD"]
    }
    
    cols = st.columns(len(suggested))
    for i, (category, tickers) in enumerate(suggested.items()):
        with cols[i]:
            st.write(f"**{category}**")
            for t in tickers:
                if st.button(f"➕ {t}", key=f"suggest_{t}"):
                    if t not in st.session_state.my_watchlist:
                        st.session_state.my_watchlist.append(t)
                        st.rerun()

    st.divider()

    # --- ส่วนจัดการหุ้นเดิม (Watchlist Management) ---
    with st.expander("""🛠️ จัดการรายชื่อหุ้น (เพิ่มเอง / ลบหุ้น)"""):
        col_in, col_add = st.columns([3, 1])
        with col_in:
            new_ticker = st.text_input("""ระบุชื่อหุ้นที่ต้องการเพิ่ม (เช่น CPALL.BK):""").upper().strip()
        with col_add:
            st.write(""" """)
            if st.button("""➕ เพิ่มเข้า List"""):
                if new_ticker and new_ticker not in st.session_state.my_watchlist:
                    st.session_state.my_watchlist.append(new_ticker)
                    st.rerun()
        
        st.write("""📋 รายการปัจจุบัน""")
        if st.session_state.my_watchlist:
            for ticker in st.session_state.my_watchlist:
                c_name, c_del = st.columns([5, 1])
                c_name.write(f"🔹 {ticker}")
                if c_del.button("""❌""", key=f"del_{ticker}"):
                    st.session_state.my_watchlist.remove(ticker)
                    st.rerun()

    # Sidebar Settings
    st.sidebar.header("""Settings""")
    itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
    itv_label = st.sidebar.selectbox("""หน่วยเวลา:""", list(itv_map.keys()))
    itv_code = itv_map[itv_label]

    # --- 5. แสดงตารางสแกนสัญญาณ ---
    st.subheader(f"""🎯 ผลการสแกนสัญญาณ ({itv_label})""")
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
        st.info("""กรุณาเพิ่มชื่อหุ้น""")

    st.divider()
    
    # --- 6. ส่วนแสดงกราฟ ---
    if st.session_state.my_watchlist:
        selected = st.selectbox("""🔍 วิเคราะห์กราฟรายตัว:""", st.session_state.my_watchlist)
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
