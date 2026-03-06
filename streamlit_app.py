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
        p, r, s = last['Close'], last['RSI'], last['SMA200']
        # Logic: ซื้อเมื่อราคา > SMA200 และ RSI < 40
        sig = "🟢 BUY" if p > s and r < 40 else "🔴 EXIT" if p < s else "WAIT"
        results.append({"หุ้น": t, "ราคา": f"{p:,.2f}", "RSI": round(r,1), "สัญญาณ": sig})

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# --- 5. ระบบจัดการหุ้น (Watchlist) ---
st.divider()
with st.expander("""🛠️ จัดการรายชื่อหุ้นใน List"""):
    c1, c2 = st.columns([3, 1])
    with c1:
        new_ticker = st.text_input("""ระบุชื่อหุ้นใหม่ (เช่น PTT.BK):""").upper().strip()
    with c2:
        st.write(""" """)
        if st.button("""➕ เพิ่มหุ้น"""):
            if new_ticker and new_ticker not in st.session_state.my_watchlist:
                st.session_state.my_watchlist.append(new_ticker)
                st.rerun()
    
    for t in st.session_state.my_watchlist:
        col_a, col_b = st.columns([5, 1])
        col_a.write(f"🔹 {t}")
        if col_b.button(f"❌", key=f"del_{t}"):
            st.session_state.my_watchlist.remove(t)
            st.rerun()

# --- 6. กราฟเทคนิค ---
st.divider()
if st.session_state.my_watchlist:
    selected = st.selectbox("""🔍 เลือกดูตัวอย่างกราฟ:""", st.session_state.my_watchlist)
    plot_df = fetch_stock_data(selected, itv_code)
    if plot_df is not None:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
