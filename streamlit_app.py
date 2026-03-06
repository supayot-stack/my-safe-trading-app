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
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "AAPL"]

# --- 2. ENGINE (RSI, SMA, RVOL, SQUEEZE) ---
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

# --- 3. SIDEBAR ---
st.sidebar.header("⚙️ Settings")
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_label = st.sidebar.selectbox("หน่วยเวลา:", list(itv_map.keys()))
itv_code = itv_map[itv_label]

st.title("🛡️ Safe Heaven Quant Pro")

# --- 4. CHART (TOP SECTION) ---
if st.session_state.my_watchlist:
    sel = st.selectbox("🔍 เลือกหุ้นวิเคราะห์กราฟ:", st.session_state.my_watchlist)
    p_df = fetch_data(sel, itv_code)
    if p_df is not None:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=p_df.index, open=p_df['Open'], high=p_df['High'], low=p_df['Low'], close=p_df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=p_df.index, y=p_df['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=p_df.index, y=p_df['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# --- 5. SCANNER TABLE (3 MODES IN ONE) ---
st.divider()
st.subheader(f"🎯 ตารางสแกนสัญญาณ ({itv_label})")
res = []
for t in st.session_state.my_watchlist:
    d = fetch_data(t, itv_code)
    if d is not None:
        l = d.iloc[-1]
        p, r, s, rv, sq = l['Close'], l['RSI'], l['SMA200'], l['RVOL'], l['SQZ']
        # Signal Logic
        trend = "🟢 BUY" if p > s and r < 40 else "🔴 EXIT" if p < s else "WAIT"
        vol = "🔥 HIGH" if rv > 2 else "Normal"
        sqz = "💎 SQZ" if sq else "Released"
        res.append({"หุ้น": t, "ราคา": f"{p:,.2f}", "Trend": trend, "RVOL": round(rv,2
