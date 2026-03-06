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

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # SMA & RSI
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # RVOL
        df['Vol_Avg'] = df['Volume'].rolling(20).mean()
        df['RVOL'] = df['Volume'] / (df['Vol_Avg'] + 1e-9)
        
        # Squeeze Logic
        df['MA20'] = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['UB'] = df['MA20'] + (2 * std)
        df['LB'] = df['MA20'] - (2 * std)
        
        # TR calculation (Stable version)
        h_l = df['High'] - df['Low']
        h_pc = (df['High'] - df['Close'].shift(1)).abs()
        l_pc = (df['Low'] - df['Close'].shift(1)).abs()
        tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
        atr = tr.rolling(20).mean()
        
        df['UK'] = df['MA20'] + (1.5 * atr)
        df['LK'] = df['MA20'] - (1.5 * atr)
        df['Sqz'] = (df['LB'] > df['LK']) & (df['UB'] < df['UK'])
        
        return df
    except: return None

# --- 3. SIDEBAR ---
st.sidebar.title("🧭 Navigator")
mode = st.sidebar.radio("กลยุทธ์:", [
    "Trend Follower (SMA+RSI)", 
    "Volume Hunter (RVOL)", 
    "Volatility Squeeze"
])
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_label = st.sidebar.selectbox("หน่วยเวลา:", list(itv_map.keys()))
itv_code = itv_map[itv_label]

# --- 4. MAIN CONTENT ---
st.title(f"🛡️ {mode}")

res = []
for t in st.session_state.my_watchlist:
    d = fetch_data(t, itv_code)
    if d is not None:
        l = d.iloc[-1]
        if mode == "Trend Follower (SMA+RSI)":
            p, r, s = l['Close'], l['RSI'], l['SMA200']
            sig = "🟢 BUY" if p > s and r < 40 else "🔴 EXIT" if p < s else "⏳ WAIT"
            res.append({"หุ้น": t, "สัญญาณ": sig, "ราคา": f"{p:,.2f}", "RSI": round(r,1)})
            
        elif mode == "Volume Hunter (RVOL)":
            rv = l['RVOL']
            stat = "🔥 HIGH" if rv > 2 else "Normal"
            res.append({"หุ้น": t, "สถานะ": stat, "RVOL": round(rv,2), "Volume": f"{l['Volume']:,.0f}"})
            
        elif mode == "Volatility Squeeze":
            is_sqz = "💎 SQUEEZING" if l['Sqz'] else "✅ Released"
            res.append({"หุ้น": t, "สถานะ": is_sqz, "ราคาล่าสุด": f"{l['Close']:,.2f}"})

# แสดงตารางผลลัพธ์
if res:
    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

# --- 5. MANAGEMENT & TOP 5 ---
st.divider()
c1, c2 = st.columns([2, 1])

with c1:
    with st.expander("🛠️ จัดการ Watchlist", expanded=False):
        new_t = st.text_input("เพิ่มชื่อหุ้น:").upper().strip()
        if st.button("บันทึกเข้าลิสต์"):
            if new_t and new_t not in st.session_state.my_watchlist:
                st.session_state.my_watchlist.append(new_t)
                st.rerun()
        st.write("---")
        for t in st.session_state.my_watchlist:
            col_a, col_b = st.columns([5, 1])
            col_a.write(f"🔹 {t}")
            if col_b.button("❌", key=f"del_{t}"):
                st.session_state.my_watchlist.remove(t)
                st.rerun()

with c2:
    st.subheader("🔍 Quick Add")
    top_5 = ["TSLA", "AAPL", "NVDA", "BTC-USD", "^SET.BK"]
    for h in top_5:
        if st.button(f"➕ {h}", key=f"q_{h}", use_container_width=True):
            if h not in st.session_state.my_watchlist:
                st.session_state.my_watchlist.append(h)
                st.rerun()

# --- 6. CHART ---
st.divider()
sel = st.selectbox("📊 เลือกดูวิเคราะห์กราฟ:", st.session_state.my_watchlist)
p_df = fetch_data(sel, itv_code)
if p_df is not None:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
    fig.add_trace(go.Candlestick(x=p_df.index, open=p_df['Open'], high=p_df['High'], low=p_df['Low'], close=p_df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=p_df.index, y=p_df['SMA200'], name='SMA 200', line=dict(color='#FFD700')), row=1, col=1)
    fig.add_trace(go.Scatter(x=p_df.index, y=p_df['RSI'], name='RSI', line=dict(color='#00FFFF')), row=2, col=1)
    fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
