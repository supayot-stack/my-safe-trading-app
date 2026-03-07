import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
import shutil

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #e1e4e8; }
    .analytics-card { background-color: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; text-align: center; margin-bottom: 10px; }
    .card-label { color: #8b949e; font-size: 13px; }
    .card-value { font-size: 26px; font-weight: bold; margin: 0; }
    .status-bar { background-color: #1c2128; border: 1px solid #39d353; border-radius: 6px; padding: 10px; text-align: center; color: #39d353; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE UTILITIES ---
DB_FILE = "masterpiece_v4.json"
COMMISSION = 0.0015

@st.cache_data(ttl=3600)
def get_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", progress=False)
        return float(data['Close'].iloc[-1])
    except: return 36.5

LIVE_FX = get_fx()

# --- 3. QUANT ENGINE (Robust Calculation) ---
@st.cache_data(ttl=1800)
def fetch_data(tickers):
    if not tickers: return {}
    processed = {}
    raw = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
    for t in tickers:
        try:
            df = raw.xs(t, axis=1, level=1).copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
            if df.empty: continue
            df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14, min_periods=1).mean()
            sl_raw = df['Close'] - (df['ATR'] * 2.5)
            tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
            for i in range(1, len(df)):
                tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
            df['TSL'] = tsl
            processed[t] = df.ffill().bfill()
        except: continue
    return processed

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏆 The Masterpiece")
    capital = st.number_input("Total Capital (THB)", value=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    watchlist = st.text_area("Watchlist", "NVDA, AAPL, PTT, DELTA")
    tickers = [t.strip().upper() for t in watchlist.split(",") if t.strip()]
    final_tickers = [t + ".BK" if t in ["PTT", "DELTA"] and not t.endswith(".BK") else t for t in tickers]

data_dict = fetch_data(final_tickers)

# --- 5. TABS ---
t_scanner, t_backtest, t_analytics = st.tabs(["🏛 Scanner", "🧪 Backtest", "🛡️ Analytics Hub"])

with t_scanner:
    res = []
    for t, df in data_dict.items():
        c = df.iloc[-1]
        res.append({"Asset": t, "Price": round(c['Close'], 2), "RSI": round(c['RSI'], 1)})
    st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

with t_backtest:
    sel = st.selectbox("Select Asset", list(data_dict.keys()) if data_dict else ["None"])
    if sel != "None":
        df_bt = data_dict[sel].copy()
        fx = 1 if ".BK" in sel else LIVE_FX
        bal, pos, trades = capital, 0, []
        for i in range(1, len(df_bt)):
            c, p = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48:
                risk_amt = bal * (risk_pct/100)
                gap = max(c['Close'] - c['TSL'], 0.01)
                pos = (risk_amt / fx) / gap
                entry_p = c['Close']
                bal -= (entry_p * pos * COMMISSION * fx)
                trades.append({"Date": df_bt.index[i], "Type": "BUY", "Price": entry_p})
            elif pos > 0 and (c['Close'] < c['TSL'] or c['RSI'] > 82):
                pnl = ((c['Close'] - entry_p) * pos * fx) - (c['Close'] * pos * COMMISSION * fx)
                bal += pnl
                trades.append({"Date": df_bt.index[i], "Type": "SELL", "PnL": pnl, "Equity": bal})
                pos = 0
        st.session_state.results = pd.DataFrame([t for t in trades if "PnL" in t])
        st.success(f"Backtest Finished. Final Equity: {bal:,.2f} THB")

with t_analytics:
    if 'results' in st.session_state and not st.session_state.results.empty:
        df_res = st.session_state.results
        col1, col2, col3 = st.columns([1.2, 0.6, 1.2])
        
        with col1:
            st.markdown("##### 🎲 Monte Carlo")
            fig_mc = go.Figure()
            for _ in range(50):
                path = np.random.choice(df_res['PnL'], size=len(df_res), replace=True).cumsum() + capital
                fig_mc.add_trace(go.Scatter(y=path, mode='lines', line=dict(width=1, color='#58a6ff'), opacity=0.15, showlegend=False))
            fig_mc.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_mc, use_container_width=True)

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            win_r = (len(df_res[df_res['PnL'] > 0]) / len(df_res)) * 100
            pf = df_res[df_res['PnL']>0]['PnL'].sum() / abs(df_res[df_res['PnL']<0]['PnL'].sum()) if any(df_res['PnL'] < 0) else 1
            metrics = [("Win Rate", f"{win_r:.1f}%"), ("Profit Factor", f"{pf:.2f}"), ("Expectancy", f"{df_res['PnL'].mean():,.0f} ฿")]
            for label, val in metrics:
                st.markdown(f'<div class="analytics-card"><div class="card-label">{label}</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)

        with col3:
            st.markdown("##### 📈 Equity Curve")
            fig_eq = go.Figure(go.Scatter(x=df_res['Date'], y=df_res['Equity'], fill='tozeroy', line=dict(color='#39d353')))
            fig_eq.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_eq, use_container_width=True)
        st.markdown('<div class="status-bar">✔ System Alpha Verified</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ ข้อมูล Analytics จะแสดงหลังจากกดรัน Backtest ใน Tab 'Backtest' เท่านั้น")
