import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. UI CONFIG (Institutional Dark) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    div[data-testid="stMetric"] {
        background-color: #1b2128; 
        padding: 20px !important; 
        border-radius: 12px; 
        border: 1px solid #30363d; 
    }
    div[data-testid="stMetricValue"] { color: #2ea043 !important; font-family: 'Courier New', monospace; }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ROBUST DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_fx():
    try:
        d = yf.download("USDTHB=X", period="1d", progress=False)
        return float(d['Close'].iloc[-1]) if not d.empty else 36.5
    except: return 36.5

LIVE_USDTHB = get_fx()

@st.cache_data(ttl=1800)
def fetch_data(tickers):
    if not tickers: return {}
    raw = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
    processed = {}
    for t in tickers:
        try:
            df = raw.xs(t, axis=1, level=1).copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
            if df.empty or len(df) < 200: continue
            
            # Indicators (หัวใจของข้อมูล)
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            df['TSL'] = df['Close'] - (df['ATR'] * 2.5)
            df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
            processed[t] = df.ffill().dropna()
        except: continue
    return processed

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🏆 THE MASTERPIECE")
    capital = st.number_input("Total Equity (THB)", value=1000000)
    risk_pct = st.slider("Risk (%)", 0.1, 5.0, 1.0)
    watchlist = st.text_area("Watchlist:", "NVDA, AAPL, PTT.BK, DELTA.BK")
    tickers = [t.strip().upper() for t in watchlist.split(",") if t.strip()]

# --- 4. PRE-CALCULATE EVERYTHING (เพื่อให้ข้อมูลขึ้นครบ) ---
data_dict = fetch_data(tickers)
ready_td_df = pd.DataFrame() # ตัวแปรนี้จะถูกส่งไป Analytics Hub

if data_dict:
    # บังคับรัน Backtest จากหุ้นตัวแรกทันที เพื่อสร้างข้อมูลส่งให้ Analytics
    main_t = list(data_dict.keys())[0]
    df_bt = data_dict[main_t].copy()
    fx = 1 if ".BK" in main_t else LIVE_USDTHB
    bal, pos, trades = capital, 0, []

    for i in range(1, len(df_bt)):
        c, p = df_bt.iloc[i], df_bt.iloc[i-1]
        if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48:
            pos = int((bal * (risk_pct/100) / fx) / max(c['Close'] - c['TSL'], 0.1))
            entry_p = c['Close']
        elif pos > 0 and (c['Close'] < c['TSL'] or c['RSI'] > 82):
            pnl = (c['Close'] - entry_p) * pos * fx
            bal += pnl
            trades.append({"Date": df_bt.index[i], "PnL": pnl, "Equity": bal})
            pos = 0
    ready_td_df = pd.DataFrame(trades)

# --- 5. DISPLAY TABS ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "🛡️ Analytics Hub", "📖 Logic"])

with tabs[2]: # Analytics Hub
    if not ready_td_df.empty:
        c1, c2, c3 = st.columns([3, 1.2, 3], gap="large")
        with c1:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            fig_mc = go.Figure()
            pnl_vals = ready_td_df['PnL'].values
            for _ in range(60):
                # สีด้านซ้ายคงเดิม: #58a6ff
                sim = capital + np.random.choice(pnl_vals, size=len(pnl_vals), replace=True).cumsum()
                fig_mc.add_trace(go.Scatter(y=sim, mode='lines', line=dict(color='#58a6ff', width=1), opacity=0.15, showlegend=False))
            fig_mc.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig_mc, use_container_width=True)

        with c2:
            st.metric("Win Rate", f"{(len(ready_td_df[ready_td_df['PnL']>0])/len(ready_td_df)*100):.1f}%")
            st.metric("Avg P/L", f"{ready_td_df['PnL'].mean():,.0f} ฿")
            st.metric("Max DD", f"{((ready_td_df['Equity']-ready_td_df['Equity'].cummax())/ready_td_df['Equity'].cummax()).min()*100:.1f}%")

        with c3:
            st.markdown("##### 📈 Equity Curve")
            fig_eq = go.Figure(go.Scatter(x=ready_td_df['Date'], y=ready_td_df['Equity'], mode='lines', line=dict(color='#2ea043', width=2), fill='tozeroy', fillcolor='rgba(46, 160, 67, 0.05)'))
            fig_eq.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig_eq, use_container_width=True)
    else:
        st.info("⚠️ ระบบกำลังรอข้อมูลจาก Watchlist ของคุณ...")

with tabs[0]: # Scanner
    if data_dict:
        res = []
        for t, df in data_dict.items():
            curr = df.iloc[-1]
            sig = "🟢 ACCUMULATE" if curr['Close'] > curr['SMA200'] and curr['RSI'] < 50 else "⚪ WAIT"
            res.append({"Asset": t, "Price": round(curr['Close'], 2), "Signal": sig, "RSI": round(curr['RSI'], 1)})
        st.dataframe(pd.DataFrame(res), use_container_width=True, hide_index=True)

st.divider(); st.caption("🏆 THE MASTERPIECE | Institutional Systematic OS")
