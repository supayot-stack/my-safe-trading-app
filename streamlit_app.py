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
    .stMetric { background-color: #161b22; padding: 10px; border-radius: 5px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE ENGINE ---
DB_FILE = "portfolio_data.json"

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=1800)
def get_data(ticker):
    try:
        # Thai Stock Auto-suffix logic
        ticker_final = ticker
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper():
            thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF", "PTTEP", "OR"]
            if ticker in thai_list: ticker_final = ticker + ".BK"
        
        df = yf.download(ticker_final, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Core Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        # RSI 14
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # Volatility (ATR) & Risk SL
        tr = pd.concat([df['High']-df['Low'], 
                       abs(df['High']-df['Close'].shift()), 
                       abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        
        # Volume Force
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']
        
        return df.dropna()
    except: return None

# --- 4. SIDEBAR (Control Center) ---
with st.sidebar:
    st.title("🏦 Personal Quant")
    capital = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0, 0.1)
    
    st.divider()
    watchlist = st.multiselect("Watchlist:", 
                               ["NVDA", "AAPL", "BTC-USD", "SET50.BK", "GOLD", "PTT", "CPALL", "TSLA"], 
                               default=["NVDA", "BTC-USD"])
    custom = st.text_input("➕ Add Ticker (e.g. TSLA):").upper().strip()
    
    final_watchlist = list(set(watchlist + ([custom] if custom else [])))

# --- 5. DATA PROCESSING ---
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
                
                # Logic: Trend + Momentum + Volume
                if p > s200 and p > s50 and r < 45 and vr > 1.2: signal = "🟢 ACCUMULATE"
                elif r > 75: signal = "💰 DISTRIBUTION"
                elif p < s200: signal = "🔴 BEARISH"
                else: signal = "⚪ NEUTRAL"

                # Risk Management Calculation
                risk_cash = capital * (risk_pct / 100)
                sl_gap = p - l['SL']
                qty = int(risk_cash / sl_gap) if sl_gap > 0 else 0

                results.append({
                    "Asset": ticker, "Price": round(p, 2), "Regime": signal,
                    "RSI": round(r, 1), "Vol-Force": f"{vr:.2f}x", 
                    "Target Qty": qty, "Stop-Loss": round(l['SL'], 2)
                })

# --- 6. MAIN TERMINAL (Tabs Interface) ---
t1, t2, t3, t4 = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "📖 Guide"])

with t1:
    st.subheader("📊 Market Opportunities")
    if results:
        res_df = pd.DataFrame(results)
        st.dataframe(res_df, use_container_width=True, hide_index=True)
        
        st.write("### 📢 Trading Action")
        for r in results:
            if r['Regime'] == "🟢 ACCUMULATE":
                st.success(f"🔥 **{r['Asset']}**: Buy Setup! Volume ratio is high ({r['Vol-Force']}). Buy {r['Target Qty']:,} units.")
            elif r['Regime'] == "💰 DISTRIBUTION":
                st.warning(f"⚠️ **{r['Asset']}**: Overbought ({r['RSI']}). Time to trim profits.")

with t2:
    if data_dict:
        sel = st.selectbox("Select Asset to Analyze:", list(data_dict.keys()))
        df_p = data_dict[sel]
        
        # Pro Layout with Volume & RSI
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                          vertical_spacing=0.03, 
                          row_heights=[0.5, 0.15, 0.35])
        
        # Price & Indicators
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], 
                                     low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Dynamic SL', line=dict(color='red', dash='dot')), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

        # Volume Force
        colors = ['#3fb950' if c >= o else '#f85149' for o, c in zip(df_p['Open'], df_p['Close'])]
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color=colors), row=3, col=1)
        
        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with t3:
    st.subheader("💼 Active Holdings & P/L")
    
    with st.expander("➕ Log New Trade"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", final_watchlist)
        p_entry = c2.number_input("Entry Price", value=0.0)
        p_qty = c3.number_input("Quantity", value=0)
        if st.button("Save Trade"):
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio)
            st.success("Portfolio Updated!")
            st.rerun()

    if st.session_state.my_portfolio:
        p_data = []
        total_pnl = 0
        for asset, info in list(st.session_state.my_portfolio.items()):
            curr_data = next((item for item in results if item["Asset"] == asset), None)
            if curr_data:
                cp = curr_data["Price"]
                unrealized = (cp - info['entry']) * info['qty']
                total_pnl += unrealized
                p_data.append({
                    "Asset": asset, "Cost": info['entry'], "Current": cp,
                    "Qty": info['qty'], "P/L (THB)": round(unrealized, 2),
                    "Status": "🚨 SELL" if cp < curr_data["Stop-Loss"] else "✅ HOLD"
                })
        
        if p_data:
            st.dataframe(pd.DataFrame(p_data), use_container_width=True, hide_index=True)
            st.metric("Total Unrealized P/L", f"{total_pnl:,.2f} THB", delta=f"{total_pnl:,.2f}")
            
            if st.button("Clear All Data"):
                st.session_state.my_portfolio = {}
                save_portfolio({})
                st.rerun()

with t4:
    st.header("📖 User Guide")
    st.markdown("""
    1. **🏛 Scanner:** มองหาหุ้นที่มีสถานะ `🟢 ACCUMULATE`
    2. **📈 Deep-Dive:** ตรวจสอบกราฟแท่งเทียนและ Volume ก่อนตัดสินใจ
    3. **💼 Portfolio:** บันทึกราคาต้นทุน เพื่อให้ระบบช่วยเฝ้าระวังจุด Stop-Loss
    4. **🛡 Risk:** อย่าซื้อเกินจำนวน `Target Qty` เพื่อจำกัดความเสี่ยงตามแผน
    """)
