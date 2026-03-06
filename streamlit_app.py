import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETUP & STYLE ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")
st.markdown("""<style>.stApp { background-color: #0e1117; color: #ffffff; }</style>""", unsafe_allow_html=True)

if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["^SET50.BK", "PTT.BK", "BTC-USD", "NVDA", "AAPL"]

# --- 2. ENGINE (SMA 200 & RSI) ---
@st.cache_data(ttl=300)
def fetch_stock_data(ticker, interval):
    try:
        p = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
        if df is None or df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicator Calculation
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        return df
    except: return None

# --- 3. DISPLAY SCANNER ---
st.title("""🛡️ Safe Heaven Quant Pro""")
st.sidebar.header("""⚙️ Settings""")
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
itv_label = st.sidebar.selectbox("""เลือกหน่วยเวลา:""", list(itv_map.keys()))
itv_code = itv_map[itv_label]

st.subheader(f"""🎯 สแกนสัญญาณเทคนิค ({itv_label})""")
results = []
for t in st.session_state.my_watchlist:
    d = fetch_stock_data(t, itv_code)
    if d is not None:
        l = d.iloc[-1]
        p, r, s = l['Close'], l['RSI'], l['SMA200']
        # บรรทัด Logic ที่คุณสั่งให้บันทึก
        sig = "🟢 BUY" if p > s and r < 40 else "🔴 EXIT" if p < s else "WAIT"
        results.append({"หุ้น": t, "ราคา": f"{p:,.2f}", "RSI": round(r,1), "สัญญาณ": sig})

if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

# --- 4. TOP 5 & WATCHLIST MANAGEMENT ---
st.divider()
with st.expander("""🛠️ จัดการรายชื่อหุ้น (เพิ่มหุ้นแนะนำ / ลบหุ้น)"""):
    st.write("""💡 **หุ้นยอดนิยม Top 5 (คลิกเพื่อเพิ่ม):**""")
    top_5 = ["TSLA", "AAPL", "NVDA", "BTC-USD", "^SET.BK"]
    cols = st.columns(len(top_5))
    for i, h in enumerate(top_5):
        if cols[i].button(f"➕ {h}", key=f"t_{h}"):
            if h not in st.session_state.my_watchlist:
                st.session_state.my_watchlist.append(h)
                st.rerun()
    
    st.divider()
    c1, c2 = st.columns([3, 1])
    new_ticker = c1.text_input("""ระบุชื่อหุ้นใหม่:""").upper().strip()
    if c2.button("""➕ เพิ่มเข้า List"""):
        if new_ticker and new_ticker not in st.session_state.my_watchlist:
            st.session_state.my_watchlist.append(new_ticker)
            st.rerun()
    
    for t in st.session_state.my_watchlist:
        ca, cb = st.columns([5, 1])
        ca.write(f"🔹 {t}")
        if cb.button(f"❌", key=f"d_{t}"):
            st.session_state.my_watchlist.remove(t)
            st.rerun()

# --- 5. CHARTING ---
st.divider()
if st.session_state.my_watchlist:
    sel = st.selectbox("""🔍 เลือกดูตัวอย่างกราฟ:""", st.session_state.my_watchlist)
    p_df = fetch_stock_data(sel, itv_code)
    if p_df is not None:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=p_df.index, open=p_df['Open'], high=p_df['High'], low=p_df['Low'], close=p_df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=p_df.index, y=p_df['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=p_df.index, y=p_df['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible
