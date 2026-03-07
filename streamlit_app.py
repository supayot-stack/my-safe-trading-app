import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Ultimate Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .market-on { color: #3fb950; font-weight: bold; }
    .market-off { color: #f85149; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE ---
DB_FILE = "portfolio_data.json"
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=1800)
def get_data(ticker):
    try:
        t_map = {"PTT": "PTT.BK", "CPALL": "CPALL.BK", "DELTA": "DELTA.BK", "SET": "^SET.BK", "SP500": "^GSPC"}
        ticker_final = t_map.get(ticker, ticker)
        df = yf.download(ticker_final, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
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

# --- 4. MARKET REGIME CHECK ---
with st.spinner("Checking Market Weather..."):
    sp500 = get_data("SP500")
    set_idx = get_data("SET")
    m_status = "BULLISH" if sp500['Close'].iloc[-1] > sp500['SMA200'].iloc[-1] else "BEARISH"
    m_color = "market-on" if m_status == "BULLISH" else "market-off"

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Ultimate Quant")
    st.markdown(f"Market Regime: <span class='{m_color}'>{m_status}</span>", unsafe_allow_html=True)
    capital = st.number_input("Total Capital (THB):", value=1000000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0)
    st.divider()
    watchlist = st.multiselect("Watchlist:", ["NVDA", "AAPL", "TSLA", "BTC-USD", "ETH-USD", "GOLD", "PTT", "CPALL", "DELTA"], default=["NVDA", "BTC-USD"])
    final_watchlist = list(set(watchlist))

# --- 6. PROCESSING & TABS ---
results = []
close_prices = {}
for t in final_watchlist:
    df = get_data(t)
    if df is not None:
        l = df.iloc[-1]
        close_prices[t] = df['Close']
        results.append({"Asset": t, "Price": l['Close'], "RSI": l['RSI'], "Vol_Ratio": l['Vol_Ratio'], "SL": l['SL']})

res_df = pd.DataFrame(results)
t1, t2, t3, t4 = st.tabs(["🏛 Scanner", "💼 Portfolio & Risk", "📈 Analysis", "🛡 Safety"])

with t1:
    st.subheader("📊 Scanner Results")
    st.dataframe(res_df, use_container_width=True, hide_index=True)

with t2:
    st.subheader("💼 Active Portfolio")
    # Log trade
    with st.expander("➕ Log Trade"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", final_watchlist)
        p_entry = c2.number_input("Entry Price")
        p_qty = c3.number_input("Qty", step=1)
        if st.button("Save"):
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty, "date": str(datetime.now().date())}
            save_portfolio(st.session_state.my_portfolio); st.rerun()

    if st.session_state.my_portfolio:
        p_list = []
        for a, info in st.session_state.my_portfolio.items():
            curr = next((x for x in results if x['Asset'] == a), None)
            if curr:
                pnl = (curr['Price'] - info['entry']) * info['qty']
                p_list.append({"Asset": a, "Cost": info['entry'], "Price": curr['Price'], "Qty": info['qty'], "P/L": pnl})
        
        st.dataframe(pd.DataFrame(p_list), use_container_width=True)
        
        # 🔗 Correlation Secret
        if len(p_list) > 1:
            st.markdown("### 🔗 Asset Correlation (Risk Check)")
            corr = pd.DataFrame({a: close_prices[a] for a in st.session_state.my_portfolio.keys()}).corr()
            st.write("ถ้าค่าใกล้ 1.0 แปลว่าหุ้นวิ่งเหมือนกันเกินไป เสี่ยง!")
            st.dataframe(corr.style.background_gradient(cmap='coolwarm'))

with t3:
    st.subheader("📈 Equity Performance")
    # Simulate Equity Curve from current holdings
    if st.session_state.my_portfolio:
        equity_data = pd.DataFrame({a: close_prices[a] * info['qty'] for a, info in st.session_state.my_portfolio.items()}).sum(axis=1)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=equity_data.index, y=equity_data, name="Portfolio Value", line=dict(color='#3fb950')))
        fig.update_layout(template="plotly_dark", title="Unrealized Equity Curve (Recent 2Y)")
        st.plotly_chart(fig, use_container_width=True)
        

with t4:
    st.subheader("🛡 Safety First")
    st.write("สำรองข้อมูลพอร์ตของคุณไว้เสมอ")
    data_str = json.dumps(st.session_state.my_portfolio)
    st.download_button("💾 Download Portfolio Backup", data_str, file_name="my_quant_backup.json")
    if st.button("🗑 Reset All"):
        save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()
