import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. Config ---
st.set_page_config(page_title="Safe Heaven", layout="wide")

if 'list' not in st.session_state:
    st.session_state.list = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA"]

# --- 2. Engine ---
@st.cache_data(ttl=300)
def get_data(symbol, itv):
    p = "2y" if itv == "1d" else "60d"
    df = yf.download(symbol, period=p, interval=itv, 
                     auto_adjust=True, progress=False)
    if df is None or df.empty or len(df) < 200: return None
    if isinstance(df.columns, pd.MultiIndex): 
        df.columns = df.columns.get_level_values(0)
    
    # Indicators
    df['MA'] = df['Close'].rolling(200).mean()
    diff = df['Close'].diff()
    g = diff.where(diff > 0, 0).rolling(14).mean()
    l = -diff.where(diff < 0, 0).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (g / (l + 1e-9))))
    return df

# --- 3. Sidebar (แก้จุดที่ Error) ---
st.sidebar.header("Settings")
# แยก Dict ออกมาไม่ให้บรรทัดยาวเกินไป
m = {"Day": "1d", "1 Hour": "1h", "5 Min": "5m"}
itv_lab = st.sidebar.selectbox("Timeframe", list(m.keys()))
itv = m[itv_lab]

# --- 4. Table ---
st.title("🛡️ Safe Heaven Quant Pro")
res = []
for s in st.session_state.list:
    d = get_data(s, itv)
    if d is not None:
        last = d.iloc[-1]
        p, r, ma = last['Close'], last['RSI'], last['MA']
        # Signal
        if p > ma and r < 40: sig = "🟢 BUY"
        elif p < ma: sig = "🔴 EXIT"
        else: sig = "WAIT"
        res.append({"Stock": s, "Price": f"{p:,.2f}", 
                    "RSI": round(r,1), "Signal": sig})

if res:
    st.dataframe(pd.DataFrame(res), use_container_width=True)

# --- 5
