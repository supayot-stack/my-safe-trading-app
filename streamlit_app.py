import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="My Personal Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .status-box { padding: 15px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid; }
    .buy-zone { background-color: #1b281b; border-color: #3fb950; color: #3fb950; }
    .warning-zone { background-color: #2d1f1f; border-color: #f85149; color: #f85149; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE ENGINE ---
DB_FILE = "portfolio_data.json"

def load_portfolio():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# Initialize Session State
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=1800) # Update every 30 mins
def get_data(ticker):
    try:
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper():
            thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF"]
            if ticker in thai_list: ticker += ".BK"
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
        return df.dropna()
    except: return None

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Personal Quant")
    equity = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0, 0.1)
    
    st.divider()
    watchlist = st.multiselect("Watchlist:", ["NVDA", "AAPL", "BTC-USD", "SET50.BK", "GOLD"], default=["NVDA", "BTC-USD"])
    custom = st.text_input("➕ Add Ticker:").upper().strip()
    
    final_watchlist = list(set(watchlist + ([custom] if custom else [])))

# --- 5. DATA SCANNING ---
results = []
data_dict = {}

if final_watchlist:
    with st.spinner('Updating Market Data...'):
        for ticker in final_watchlist:
            df = get_data(ticker)
            if df is not None:
                data_dict[ticker] = df
                l = df.iloc[-1]
                p, r, s200, s50, vr = l['Close'], l['RSI'], l['SMA200'], l['SMA50'], l['Vol_Ratio']
                
                # Logic
                if p > s200 and p > s50 and r < 45 and vr > 1.2: signal = "🟢 ACCUMULATE"
                elif r > 75: signal = "💰 DISTRIBUTION"
                elif p < s200: signal = "🔴 BEARISH"
                else: signal = "⚪ NEUTRAL"

                risk_cash = equity * (risk_pct / 100)
                sl_gap = p - l['SL']
                qty = int(risk_cash / sl_gap) if sl_gap > 0 else 0

                results.append({
                    "Asset": ticker, "Price": round(p, 2), "Regime": signal,
                    "RSI": round(r, 1), "Target Qty": qty, "Stop-Loss": round(l['SL'], 2)
                })

# --- 6. MAIN TERMINAL ---
t1, t2, t3, t4 = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 My Portfolio", "📖 Guide"])

with t1:
    st.subheader("📊 Market Opportunities")
    if results:
        res_df = pd.DataFrame(results)
        st.dataframe(res_df, use_container_width=True, hide_index=True)
        
        # Action Summary
        st.write("### 📢 Action Center")
        for r in results:
            if r['Regime'] == "🟢 ACCUMULATE":
                st.success(f"🔥 **{r['Asset']}** อยู่ในจุดสะสมที่ได้เปรียบ (Target Qty: {r['Target Qty']:,} หุ้น)")

with t2:
    if data_dict:
        sel = st.selectbox("Select Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Stop-Loss', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with t3:
    st.subheader("💼 Active Holdings")
    
    # Form to add to portfolio
    with st.expander("➕ Add New Position"):
        c1, c2, c3 = st.columns(3)
        new_asset = c1.selectbox("Asset", final_watchlist)
        new_price = c2.number_input("Entry Price", value=0.0)
        new_qty = c3.number_input("Quantity", value=0)
        if st.button("Add to Portfolio"):
            st.session_state.my_portfolio[new_asset] = {"entry": new_price, "qty": new_qty}
            save_portfolio(st.session_state.my_portfolio)
            st.rerun()

    # Display Portfolio
    if st.session_state.my_portfolio:
        p_list = []
        total_pl = 0
        for asset, info in list(st.session_state.my_portfolio.items()):
            # Get current price from results
            curr_data = next((item for item in results if item["Asset"] == asset), None)
            if curr_data:
                curr_p = curr_data["Price"]
                sl_p = curr_data["Stop-Loss"]
                pl_val = (curr_p - info['entry']) * info['qty']
                pl_pct = ((curr_p / info['entry']) - 1) * 100
                total_pl += pl_val
                
                p_list.append({
                    "Asset": asset, "Entry": info['entry'], "Current": curr_p,
                    "Qty": info['qty'], "P/L (THB)": round(pl_val, 2), "P/L (%)": f"{pl_pct:.2f}%",
                    "Status": "🚨 EXIT" if curr_p < sl_p else "✅ HOLD"
                })
        
        if p_list:
            st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True)
            st.metric("Total Portfolio P/L", f"{total_pl:,.2f} THB", delta=f"{total_pl:,.2f}")
            
            if st.button("🗑️ Clear Portfolio"):
                st.session_state.my_portfolio = {}
                save_portfolio({})
                st.rerun()
    else:
        st.info("พอร์ตว่างเปล่า เริ่มต้นด้วยการเพิ่มหุ้นที่คุณถืออยู่")

with t4:
    st.header("📖 Personal Guide")
    st.markdown("""
    1. **Add Asset:** เพิ่มชื่อหุ้นที่ Sidebar (หุ้นไทยไม่ต้องใส่ .BK ระบบจะพยายามเติมให้)
    2. **Check Scanner:** ดูสถานะ 🟢 ACCUMULATE เพื่อหาจังหวะเข้าซื้อ
    3. **Manage Portfolio:** ใส่ราคาที่คุณซื้อจริงใน Tab 💼 เพื่อให้ระบบเฝ้าดู P/L และ Stop Loss ให้คุณ
    4. **Persistence:** ระบบจะบันทึกข้อมูลหุ้นในพอร์ตลงในเครื่องคุณโดยอัตโนมัติ
    """)
