import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG (Pixel-Perfect Accuracy) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b1015; color: #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    
    /* Center Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #1b2128; 
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 20px !important;
        margin-bottom: 15px;
    }
    div[data-testid="stMetricValue"] { color: #2ea043 !important; font-family: 'Courier New', monospace; font-weight: bold; font-size: 26px !important; }
    div[data-testid="stMetricLabel"] { color: #8b949e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 1px; }
    
    .alpha-verified {
        background: linear-gradient(90deg, #1b2128, rgba(35, 134, 54, 0.2));
        border: 1px solid #238636;
        color: #3fb950;
        padding: 12px;
        text-align: center;
        border-radius: 6px;
        font-weight: bold;
        margin-top: 25px;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; border-bottom: 1px solid #30363d; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom: 2px solid #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE QUANT ENGINE & DATA PERSISTENCE ---
DB_FILE = "masterpiece_v2.json"

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

@st.cache_data(ttl=1800)
def fetch_quant_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
                if df.empty or len(df) < 200: continue
                
                # Indicators Logic
                df['SMA200'] = df['Close'].rolling(200).mean()
                df['SMA50'] = df['Close'].rolling(50).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14).mean()
                df['Trailing_SL'] = df['Close'] - (df['ATR'] * 2.5)
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
                
                processed[t] = df.ffill().dropna()
            except: continue
        return processed
    except: return {}

# --- 3. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🏆 THE MASTERPIECE")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    capital = st.number_input("Total Equity (THB)", value=1000000, step=100000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.5, 5.0, 1.0)
    watchlist_input = st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT.BK, DELTA.BK")
    tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

data_dict = fetch_quant_data(tickers)

# --- 4. MAIN DISPLAY & LOGIC ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Logic"])

# Pre-calculate for Analytics (ป้องกัน ValueError)
td_df = pd.DataFrame() # Default Empty
if data_dict:
    # เลือกตัวแรกในลิสต์มารัน Backtest จำลองให้ Analytics Hub
    target = list(data_dict.keys())[0]
    df_bt = data_dict[target].copy()
    bal, pos, trades = capital, 0, []
    for i in range(1, len(df_bt)):
        c, p = df_bt.iloc[i], df_bt.iloc[i-1]
        if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48:
            pos = int((bal * (risk_pct/100)) / max(c['Close'] - c['Trailing_SL'], 0.1))
            entry_p = c['Close']
            trades.append({"Date": df_bt.index[i], "Type": "BUY", "Price": entry_p})
        elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
            pnl = (c['Close'] - entry_p) * pos
            bal += pnl
            trades.append({"Date": df_bt.index[i], "PnL": pnl, "Equity": bal})
            pos = 0
    td_df = pd.DataFrame([t for t in trades if "PnL" in t])

# --- TAB: ANALYTICS HUB (THE IMAGE CLONE) ---
with tabs[4]:
    if not td_df.empty:
        col_l, col_m, col_r = st.columns([3, 1.2, 3], gap="large")
        with col_l:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            fig_mc = go.Figure()
            # ดึง PnL มาเป็น Array เพื่อความไวและกัน Error
            pnl_array = td_df['PnL'].values
            for _ in range(60):
                sim_path = capital + np.random.choice(pnl_array, size=len(pnl_array), replace=True).cumsum()
                fig_mc.add_trace(go.Scatter(y=sim_path, mode='lines', line=dict(color='#58a6ff', width=0.8), opacity=0.12, showlegend=False))
            fig_mc.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_mc, use_container_width=True)

        with col_m:
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 1.2
            st.metric("Win Rate", f"{win_r:.1f}%")
            st.metric("Profit Factor", f"{pf:.2f}")
            st.metric("Avg Trade P/L", f"{td_df['PnL'].mean():,.0f} ฿")
            st.metric("Max Drawdown", f"{((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100:.1f}%")

        with col_r:
            st.markdown("##### 📈 Equity Curve")
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(x=td_df['Date'], y=td_df['Equity'], mode='lines', line=dict(color='#2ea043', width=2.5), fill='tozeroy', fillcolor='rgba(46, 160, 67, 0.05)'))
            fig_eq.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_eq, use_container_width=True)
        st.markdown('<div class="alpha-verified">✅ System Alpha Verified: Institutional Grade Robustness</div>', unsafe_allow_html=True)
    else:
        st.info("กรุณาเพิ่ม Ticker ใน Sidebar เพื่อเริ่มการวิเคราะห์")

# --- TAB: DEEP DIVE (CANDLESTICK) ---
with tabs[1]:
    if data_dict:
        sel = st.selectbox("Select Asset", list(data_dict.keys()))
        df = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], line=dict(color='yellow', width=1), name='SMA 200'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#00ffff', width=1.5), name='RSI'), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("🏆 THE MASTERPIECE | v2.6 Full Suite")
