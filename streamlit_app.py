import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Gemini Master Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .highlight-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; border-radius: 10px; border: 1px solid #3b82f6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE ENGINE ---
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
        ticker_final = ticker
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF", "PTTEP", "OR", "DELTA", "KTB"]
        if ticker in thai_list: ticker_final = ticker + ".BK"
        
        df = yf.download(ticker_final, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Core Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        df['Volatility'] = (df['ATR'] / df['Close']) * 100
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']
        return df.dropna()
    except: return None

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Personal Quant")
    capital = st.number_input("Total Capital (THB):", value=1000000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0)
    st.divider()
    default_list = ["NVDA", "AAPL", "TSLA", "MSTR", "BTC-USD", "ETH-USD", "GOLD", "PTT", "CPALL", "DELTA", "GULF", "KTB"]
    watchlist = st.multiselect("Watchlist Pool:", default_list, default=default_list)
    custom = st.text_input("➕ Add Ticker (e.g. TSLA):").upper().strip()
    final_watchlist = list(set(watchlist + ([custom] if custom else [])))

# --- 5. DATA PROCESSING ---
results = []
data_dict = {}
with st.spinner('Scanning Market Data...'):
    for ticker in final_watchlist:
        df = get_data(ticker)
        if df is not None:
            data_dict[ticker] = df
            l = df.iloc[-1]
            p, r, s200, s50, vr, vola = l['Close'], l['RSI'], l['SMA200'], l['SMA50'], l['Vol_Ratio'], l['Volatility']
            
            # Logic: Signal
            if p > s200 and p > s50 and r < 45 and vr > 1.2: sig = "🟢 ACCUMULATE"
            elif r > 75: sig = "💰 DISTRIBUTION"
            elif p < s200: sig = "🔴 BEARISH"
            else: sig = "⚪ NEUTRAL"

            # Risk Management
            risk_cash = capital * (risk_pct / 100)
            sl_gap = p - l['SL']
            qty = int(risk_cash / sl_gap) if sl_gap > 0 else 0

            results.append({
                "Asset": ticker, "Price": round(p, 2), "Regime": sig, "RSI": round(r, 1), 
                "Vol_Ratio": vr, "Volatility": vola, "Target Qty": qty, "Stop-Loss": round(l['SL'], 2)
            })

res_df = pd.DataFrame(results)

# --- 6. MAIN TERMINAL ---
t1, t2, t3, t4, t5 = st.tabs(["🏛 Scanner", "🎯 Auto Quant Picks", "📈 Deep-Dive", "💼 Portfolio", "📖 Guide"])

with t1:
    st.subheader("📊 Market Opportunities")
    if results:
        st.dataframe(res_df[["Asset", "Price", "Regime", "RSI", "Target Qty", "Stop-Loss"]], use_container_width=True, hide_index=True)

with t2:
    st.markdown("<div class='highlight-card'><h2>🎯 AI Autonomous Picks (Real-Time)</h2></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("🚀 **Momentum Kings**")
        mo_king = res_df[res_df['Regime'] != "🔴 BEARISH"].sort_values('RSI', ascending=False).head(3)
        for _, row in mo_king.iterrows(): st.write(f"**{row['Asset']}** (RSI: {row['RSI']:.1f})")
    with c2:
        st.success("🔥 **Volume Surge**")
        vol_surge = res_df.sort_values('Vol_Ratio', ascending=False).head(3)
        for _, row in vol_surge.iterrows(): st.write(f"**{row['Asset']}** (Vol: {row['Vol_Ratio']:.2f}x)")
    with c3:
        st.warning("⚡ **High Vol (Practice)**")
        high_vola = res_df.sort_values('Volatility', ascending=False).head(3)
        for _, row in high_vola.iterrows(): st.write(f"**{row['Asset']}** (Vola: {row['Volatility']:.2f}%)")

with t3:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Stop-Loss', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume'), row=3, col=1)
        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with t4:
    st.subheader("💼 Portfolio & P/L Tracking")
    with st.expander("➕ บันทึกไม้เทรด (Add Position)"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", final_watchlist)
        p_entry = c2.number_input("Entry Price", value=0.0)
        p_qty = c3.number_input("Quantity", value=0)
        if st.button("Confirm Trade"):
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio)
            st.rerun()

    if st.session_state.my_portfolio:
        p_data = []
        total_v = 0
        total_pnl = 0
        for asset, info in list(st.session_state.my_portfolio.items()):
            curr = next((item for item in results if item["Asset"] == asset), None)
            if curr:
                cp = curr["Price"]
                unrealized = (cp - info['entry']) * info['qty']
                total_pnl += unrealized
                total_v += (cp * info['qty'])
                p_data.append({"Asset": asset, "Cost": info['entry'], "Price": cp, "Qty": info['qty'], "P/L (THB)": round(unrealized, 2), "Action": "🚨 EXIT" if cp < curr["Stop-Loss"] else "✅ HOLD"})
        
        if p_data:
            st.dataframe(pd.DataFrame(p_data), use_container_width=True, hide_index=True)
            m1, m2 = st.columns(2)
            m1.metric("Portfolio Value", f"{total_v:,.2f}")
            m2.metric("Total Unrealized P/L", f"{total_pnl:,.2f}", delta=f"{total_pnl:,.2f}")
            if st.button("🗑️ Reset All Data"):
                st.session_state.my_portfolio = {}; save_portfolio({}); st.rerun()
    else: st.info("ไม่มีหุ้นในพอร์ต")

with t5:
    st.write("📖 **Guide:** Scanner บอกจุดเข้า, Auto Picks คัดหุ้นเด่น, Deep-Dive ดูกราฟ, Portfolio คุมกำไร")
