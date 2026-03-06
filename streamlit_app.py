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
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "TSLA"]

# --- 3. ฟังก์ชันดึงข้อมูลแบบ All-in-One ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # คำนวณทุกอย่างเตรียมไว้
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        df['Vol_Avg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_Avg']
        
        # Squeeze Logic
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

# --- 4. Sidebar Navigation (แยกหน้าตามกลยุทธ์) ---
st.sidebar.title("""🧭 Navigator""")
mode = st.sidebar.radio("""เลือกโหมดกลยุทธ์:""", [
    "Trend Follower (SMA+RSI)", 
    "Volume Hunter (RVOL)", 
    "Volatility Squeeze (Breakout)"
])

itv_label = st.sidebar.selectbox("""หน่วยเวลา:""", ["1 วัน", "1 ชั่วโมง", "5 นาที"])
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_code = itv_map[itv_label]

# --- 5. จัดการเนื้อหาตาม Mode ที่เลือก ---

# --- หน้าที่ 1: Trend Follower ---
if mode == "Trend Follower (SMA+RSI)":
    st.title("""🛡️ กลยุทธ์ตามเทรนด์ (Trend Follower)""")
    with st.expander("""📖 คู่มือเทคนิค: SMA 200 + RSI""", expanded=True):
        st.write("""- **Concept:** เทรดเฉพาะหุ้นขาขึ้น (ราคาเหนือเส้น 200 วัน)""")
        st.write("""- **จุดเข้า:** ซื้อเมื่อ RSI < 40 (ย่อตัวในขาขึ้น) | **จุดออก:** ขายเมื่อราคาหลุดเส้น 200 วัน""")
    
    res = []
    for t in st.session_state.my_watchlist:
        d = fetch_data(t, itv_code)
        if d is not None:
            l = d.iloc[-1]
            p, r, s = l['Close'], l['RSI'], l['SMA200']
            sig = "🟢 BUY" if p > s and r < 40 else "🔴 EXIT" if p < s else "WAIT"
            res.append({"Ticker": t, "Price": f"{p:,.2f}", "RSI": round(r,1), "SMA200": f"{s:,.2f}", "Signal": sig})
    st.table(pd.DataFrame(res))

# --- หน้าที่ 2: Volume Hunter ---
elif mode == "Volume Hunter (RVOL)":
    st.title("""📊 กลยุทธ์วอลุ่มเข้า (Volume Hunter)""")
    with st.expander("""📖 คู่มือเทคนิค: Relative Volume (RVOL)""", expanded=True):
        st.write("""- **Concept:** ตามรอยเงินก้อนใหญ่ (Smart Money)""")
        st.write("""- **วิธีดู:** ค่า RVOL > 2.0 แปลว่ามีคนซื้อขายมากกว่าปกติ 2 เท่า! เป็นสัญญาณต้นน้ำ""")
    
    res = []
    for t in st.session_state.my_watchlist:
        d = fetch_data(t, itv_code)
        if d is not None:
            l = d.iloc[-1]
            rv = l['RVOL']
            stat = "🔥 HIGH VOL" if rv > 2 else "Normal"
            res.append({"Ticker": t, "Volume": f"{l['Volume']:,.0f}", "Avg Vol (20d)": f"{l['Vol_Avg']:,.0f}", "RVOL": round(rv,2), "Status": stat})
    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

# --- หน้าที่ 3: Volatility Squeeze ---
elif mode == "Volatility Squeeze (Breakout)":
    st.title("""🚀 จุดระเบิดราคา (Volatility Squeeze)""")
    with st.expander("""📖 คู่มือเทคนิค: Bollinger Squeeze""", expanded=True):
        st.write("""- **Concept:** หาช่วงเวลาที่ราคา 'บีบตัว' เพื่อรอระเบิดแรงๆ""")
        st.write("""- **วิธีดู:** ถ้าขึ้น 'SQUEEZING' แปลว่าหุ้นเงียบผิดปกติ พร้อมจะพุ่งหรือร่วงแรงในเร็วๆ นี้""")
    
    res = []
    for t in st.session_state.my_watchlist:
        d = fetch_data(t, itv_code)
        if d is not None:
            l = d.iloc[-1]
            is_sqz = "💎 SQUEEZING" if l['Squeeze'] else "Released"
            res.append({"Ticker": t, "Price": f"{l['Close']:,.2f}", "Squeeze Status": is_sqz})
    st.table(pd.DataFrame(res))

# --- ส่วนกลาง: จัดการหุ้นและกราฟ ---
st.divider()
c1, c2 = st.columns([2, 1])
with c1:
    with st.expander("""🛠️ จัดการรายชื่อหุ้น (Watchlist)"""):
        in_t = st.text_input("""เพิ่มชื่อหุ้น (เช่น CPALL.BK):""").upper().strip()
        if st.button("""เพิ่มเข้ารายการ"""):
            if in_t and in_t not in st.session_state.my_watchlist:
                st.session_state.my_watchlist.append(in_t)
                st.rerun()
        for t in st.session_state.my_watchlist:
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"🔹 {t}")
            if col_b.button("❌", key=f"del_{t}"):
                st.session_state.my_watchlist.remove(t)
                st.rerun()

with c2:
    st.subheader("""🔍 Quick Add""")
    hot_list = ["TSLA", "AAPL", "NVDA", "BTC-USD", "^SET.BK"]
    for h in hot_list:
        if st.button(f"➕ {h}", key=f"hot_{h}"):
            if h not in st.session_state.my_watchlist:
                st.session_state.my_watchlist.append(h)
                st.rerun()

# กราฟแสดงผลตามตัวที่เลือก
st.subheader("""📊 Technical Chart""")
sel = st.selectbox("""เลือกหุ้นดูย้อนหลัง:""", st.session_state.my_watchlist)
p_df = fetch_data(sel, itv_code)
if p_df is not None:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=p_df.index, open=p_df['Open'], high=p_df['High'], low=p_df['Low'], close=p_df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=p_df.index, y=p_df['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
    fig.update_layout(height=400, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
