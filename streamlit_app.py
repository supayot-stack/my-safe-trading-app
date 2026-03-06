import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. Page Config
st.set_page_config(page_title="Safe Heaven", layout="wide")

# 2. Watchlist
if 'list' not in st.session_state:
    st.session_state.list = ["PTT.BK", "BTC-USD", "NVDA"]

# 3. Data Func
def get_data(symbol, itv):
    d = yf.download(symbol, period="2y", interval=itv, progress=False)
    if d is None or d.empty: return None
    if isinstance(d.columns, pd.MultiIndex): 
        d.columns = d.columns.get_level_values(0)
    
    # Calc SMA & RSI
    d['SMA'] = d['Close'].rolling(200).mean()
    diff = d['Close'].diff()
    g = diff.where(diff > 0, 0).rolling(14).mean()
    l = -diff.where(diff < 0, 0).rolling(14).mean()
    d['RSI'] = 100 - (100 / (1 + (g / (l + 1e-9))))
    return d

# 4. Header & Sidebar
st.title("🛡️ Safe Heaven Quant")
itv = st.sidebar.selectbox("Timeframe", ["1d", "1h", "5m"])

# 5. Scan Table
res = []
for s in st.session_state.list:
    df = get_data(s, itv)
    if df is not None:
        last = df.iloc[-1]
        p, r, ma = last['Close'], last['RSI'], last['SMA']
        # Signal Logic
        sig = "BUY" if p > ma and r < 40 else "WAIT"
        if p < ma: sig = "EXIT"
        res.append({"Stock": s, "Price": f"{p:.2f}", "RSI": int(r), "Signal": sig})

if res:
    st.table(pd.DataFrame(res))

# 6. Add/Remove
with st.expander("Manage List"):
    new = st.text_input("Symbol:").upper()
    if st.button("Add"):
        st.session_state.list.append(new)
        st.rerun()
    if st.button("Clear List"):
        st.session_state.list = []
        st.rerun()

# 7. Simple Chart
sel = st.selectbox("View Chart", st.session_state.list)
pdf = get_data(sel, itv)
if pdf is not None:
    f = go.Figure()
    f.add_trace(go.Scatter(x=pdf.index, y=pdf['Close'], name='Price'))
    f.add_trace(go.Scatter(x=pdf.index, y=pdf['SMA'], name='SMA200'))
    f.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(f, use_container_width=True)
