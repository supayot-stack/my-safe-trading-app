import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. Setup ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["PTT.BK", "BTC-USD", "NVDA", "AAPL"]

# --- 2. Data Engine ---
@st.cache_data(ttl=300)
def fetch_data(ticker, interval):
    p = "2y" if interval == "1d" else "60d"
    df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
    
    if df is None or df.empty or len(df) < 200:
        return None
        
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # คำนวณ SMA & RSI
    df['SMA'] = df['Close'].rolling(200).mean()
    diff = df['Close'].diff()
    g = (diff.where(diff > 0, 0)).rolling(14).mean()
    l = (-diff.where(diff < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (g / (l + 1e-9))))
    
    # คำนวณ RVOL
    v_avg = df['Volume'].rolling(20).mean()
    df['RVOL'] = df['Volume'] / (v_avg + 1e-9)
    
    # คำนวณ Squeeze
    m20 = df['Close'].rolling(20).mean()
    std = df['Close'].rolling(20).std()
    df['UB'] = m20 + (2 * std)
    df['LB'] = m20 - (2 * std)
    
    # True Range (แยกบรรทัดเพื่อความปลอดภัย)
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = df['TR'].rolling(20).mean()
    df['UK'] = m20 + (1.5 * atr)
    df['LK'] = m20 - (1.5 * atr)
    df['SQZ'] = (df['LB'] > df['LK']) & (df['UB'] < df['UK'])
    
    return df

# --- 3. Sidebar ---
st.sidebar.header("""⚙️ Menu""")
mode = st.sidebar.radio("""🎯 Strategy:""", ["Trend Follower", "Volume Hunter", "Squeeze Breakout"])
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_label = st.sidebar.selectbox("""⏱️ Interval:""", list(itv_map.keys()))
itv_code = itv_map[itv_label]

# --- 4. Main Content ---
st.title(f"🛡️ {mode}")

if mode == "Trend Follower":
    st.info("📖 SMA 200 + RSI: ซื้อเมื่อราคาเหนือเส้น 200 และ RSI < 40")
    res = []
    for t in st.session_state.my_watchlist:
        d = fetch_data(t, itv_code)
        if d is not None:
            last = d.iloc[-1]
            p, r, s = last['Close'], last['RSI'], last['SMA']
            sig = "🟢 BUY" if p > s and r < 40 else "💰 PROFIT" if r > 75 else "🔴 EXIT" if p < s else "WAIT"
            res.append({"หุ้น": t, "ราคา": f"{p:,.2f}", "RSI": round(r,1), "สัญญาณ": sig})
    if res: st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

elif mode == "Volume Hunter":
    st.info("📖 RVOL > 2.0: วอลุ่มเข้ามากกว่าปกติ 2 เท่า")
    res = []
    for t in st.session_state.my_watchlist:
        d = fetch_data(t, itv_code)
        if d is not None:
            last = d.iloc[-1]
            rv = last['RVOL']
            stt = "🔥 HIGH VOL" if rv > 2 else "Normal"
            res.append({"หุ้น": t, "Vol": f"{last['Volume']:,.0f}", "RVOL": round(rv, 2), "สถานะ": stt})
    if res: st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=
