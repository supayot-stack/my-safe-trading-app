import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. SETUP ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "TSLA"]

# --- 2. DATA ENGINE (จัดการกรณีข้อมูลไม่พอ) ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        # ปรับระยะเวลาให้ดึงข้อมูลได้เพียงพอต่อ SMA200
        p = "max" if interval == "1d" else "60d" 
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        
        if df is None or df.empty or len(df) < 20: return None # อย่างน้อยต้องมีข้อมูลบ้าง
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # คำนวณพื้นฐาน (SMA200 อาจเป็น NaN ได้ถ้าข้อมูลไม่ถึง 200)
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # RVOL & Squeeze
        df['V_Avg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / (df['V_Avg'] + 1e-9)
        m20 = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['UB'], df['LB'] = m20 + (2*std), m20 - (2*std)
        tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift(1)).abs(), (df['Low']-df['Close'].shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.rolling(20).mean()
        df['UK'], df['LK'] = m20 + (1.5*atr), m20 - (1.5*atr)
        df['SQZ'] = (df['LB'] > df['LK']) & (df['UB'] < df['UK'])
        
        return df
    except: return None

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.title("🧭 Navigator")
mode = st.sidebar.radio("เลือกโหมดกลยุทธ์:", [
    "Trend Follower (SMA+RSI)", 
    "Volume Hunter (RVOL)", 
    "Volatility Squeeze"
])
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_label = st.sidebar.selectbox("หน่วยเวลา:", list(itv_map.keys()))
itv_code = itv_map[itv_label]

st.title("🛡️ Safe Heaven Quant Pro")

# --- 4. TOP SECTION: CHART (ย้ายขึ้นบนสุด) ---
if st.session_state.my_watchlist:
    sel = st.selectbox("📊 วิเคราะห์กราฟรายตัว:", st.session_state.my_watchlist)
    p_df = fetch_data(sel, itv_code)
    if p_df is not None:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=p_df.index, open=p_df['Open'], high=p_df['High'], low=p_df['Low'], close=p_df['Close'], name='Price'), row=1, col=1)
        # แสดง SMA 200 เฉพาะเมื่อมีข้อมูล
        if not p_df['SMA200'].isnull().all():
            fig.add_trace(go.Scatter(x=p_df.index, y=p_df['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=p_df.index, y=p_df['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=450, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# --- 5. MIDDLE SECTION: SCANNER TABLE + MANUAL ---
st.divider()
if mode == "Trend Follower (SMA+RSI)":
    st.subheader("🛡️ กลยุทธ์ Trend Follower")
    with st.expander("📖 คู่มือเทคนิค: SMA 200 + RSI", expanded=True):
        st.write("- ซื้อเมื่อราคา > SMA200 (ขาขึ้น) และ RSI < 40 (ย่อตัว)")
elif mode == "Volume Hunter (RVOL)":
    st.subheader("📊 กลยุทธ์ Volume Hunter")
    with st.expander("📖 คู่มือเทคนิค: RVOL", expanded=True):
        st.write("- RVOL > 2.0 แปลว่ามีแรงซื้อขายมากกว่าค่าเฉลี่ย 2 เท่า")
elif mode == "Volatility Squeeze":
    st.subheader("🚀 กลยุทธ์ Volatility Squeeze")
    with st.expander("📖 คู่มือเทคนิค: Squeeze", expanded=True):
        st.write("- 💎 SQZ คือช่วงราคาบีบตัวรอนอกกรอบเพื่อระเบิดราคา")

res = []
for t in st.session_state.my_watchlist:
    d = fetch_data(t, itv_code)
    if d is not None:
        l = d.iloc[-1]
        if mode == "Trend Follower (SMA+RSI)":
            p, r, s = l['Close'], l['RSI'], l['SMA200']
            if pd.isna(s): sig = "⚠️ ข้อมูลไม่พอ (SMA200)"
            else: sig = "🟢 BUY" if p > s and r < 40 else "🔴 EXIT" if p < s else "WAIT"
            res.append({"Ticker": t, "Price": f"{p:,.2f}", "RSI": round(r,1), "Signal": sig})
        elif mode == "Volume Hunter (RVOL)":
            res.append({"Ticker": t, "RVOL": round(l['RVOL'],2), "Status": "🔥 HIGH" if l['RVOL'] > 2 else "Normal"})
        elif mode == "Volatility Squeeze":
            res.append({"Ticker": t, "Squeeze": "💎 SQZ" if l['SQZ'] else "Released"})

if res:
    st.table(pd.DataFrame(res))
