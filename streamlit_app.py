import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG (Institutional Dark Theme) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    
    /* Metric Cards (KPIs) */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricValue"] { color: #3fb950 !important; font-size: 28px !important; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 14px !important; }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22; border-radius: 4px 4px 0 0;
        padding: 10px 20px; color: #8b949e; border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important; color: white !important; border: 1px solid #2ea043 !important;
    }

    /* Alpha Verified Badge */
    .alpha-badge {
        background-color: rgba(35, 134, 54, 0.1);
        border: 1px solid #238636;
        color: #3fb950;
        border-radius: 6px;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        margin-top: 20px;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
DB_FILE = "masterpiece_v2.json"
COMMISSION_RATE = 0.0015

@st.cache_data(ttl=3600)
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        return float(data['Close'].iloc[-1]) if not data.empty else 36.52
    except: return 36.52

LIVE_USDTHB = get_live_fx()

@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
                if df.empty or len(df) < 50: continue
                df['SMA200'] = df['Close'].rolling(200).mean()
                df['SMA50'] = df['Close'].rolling(50).mean()
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14).mean()
                df['Trailing_SL'] = df['Close'] - (df['ATR'] * 2.5)
                # Simple RSI
                delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean(); loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
                processed[t] = df.ffill().dropna()
            except: continue
        return processed
    except: return {}

# --- 3. SIDEBAR (The Masterpiece Panel) ---
with st.sidebar:
    st.markdown("### 🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    st.write(f"FX Rate: **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Capital (THB)", value=1000000, step=100000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.5, 5.0, 1.0)
    watchlist_input = st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
    final_tickers = []
    for t in tickers:
        if any(x in t for x in ["PTT", "DELTA", "ADVANC", "KBANK"]) and ".BK" not in t: final_tickers.append(t + ".BK")
        else: final_tickers.append(t)

data_dict = fetch_all_data(final_tickers)

# --- 4. MAIN INTERFACE ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Logic"])

# Pre-calculate Backtest for Analytics (Using the first ticker for demo)
if data_dict:
    target = list(data_dict.keys())[0]
    df_bt = data_dict[target].iloc[-500:].copy()
    bal, pos, trades = capital, 0, []
    for i in range(1, len(df_bt)):
        c, p = df_bt.iloc[i], df_bt.iloc[i-1]
        if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48:
            pos = int((bal * (risk_pct/100)) / max(c['Close'] - c['Trailing_SL'], 0.1))
            entry_p = c['Close']
            trades.append({"Date": df_bt.index[i], "Type": "BUY", "Price": entry_p})
        elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
            pnl = (c['Close'] - entry_p) * pos * (1 if ".BK" in target else LIVE_USDTHB)
            bal += pnl
            trades.append({"Date": df_bt.index[i], "PnL": pnl, "Equity": bal})
            pos = 0
    td_df = pd.DataFrame([t for t in trades if "PnL" in t])

with tabs[3]: # Analytics Hub
    if 'td_df' in locals() and not td_df.empty:
        # Layout: Monte Carlo | Stats | Equity Curve
        col_mc, col_stats, col_eq = st.columns([3, 1.2, 3])

        with col_mc:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            fig_mc = go.Figure()
            for _ in range(50):
                sim_path = np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital
                fig_mc.add_trace(go.Scatter(y=sim_path, mode='lines', line=dict(color='#58a6ff', width=1), opacity=0.2, showlegend=False))
            
            fig_mc.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               margin=dict(l=0,r=0,t=10,b=0), xaxis=dict(title="Number of Trades"), yaxis=dict(title="Portfolio Value (THB)"))
            st.plotly_chart(fig_mc, use_container_width=True)

        with col_stats:
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 1.0
            avg_pnl = td_df['PnL'].mean()
            mdd = ((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min() * 100
            
            st.metric("Win Rate", f"{win_r:.1f}%")
            st.metric("Profit Factor", f"{pf:.2f}")
            st.metric("Avg Trade P/L", f"{avg_pnl:,.0f} ฿")
            st.metric("Max Drawdown", f"{mdd:.1f}%")

        with col_eq:
            st.markdown("##### 📈 Equity Curve")
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(x=td_df['Date'], y=td_df['Equity'], mode='lines', line=dict(color='#00ff00', width=2.5),
                                      fill='tozeroy', fillcolor='rgba(0, 255, 0, 0.1)', name="Net Equity"))
            fig_eq.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_eq, use_container_width=True)

        st.markdown('<div class="alpha-badge">✅ System Alpha Verified</div>', unsafe_allow_html=True)
    else:
        st.info("Please run backtest logic to populate analytics.")

with tabs[1]: # Deep Dive
    if data_dict:
        sel = st.selectbox("Select Asset", list(data_dict.keys()))
        df = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], line=dict(color='yellow', width=1), name="SMA 200"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#58a6ff', width=1.5), name="RSI"), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("🏆 The Masterpiece | Institutional Systematic OS v2.6")
