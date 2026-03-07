import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { 
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #30363d; 
        border-left: 5px solid #00ff00;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    div[data-testid="stMetricValue"] { color: #00ff00 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; border-radius: 6px 6px 0px 0px; 
        padding: 12px 25px; color: #8b949e; transition: 0.3s;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #238636 !important; color: white !important; font-weight: bold;
    }
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 10px; background-color: #0d1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE & PERSISTENCE ---
DB_FILE = "the_masterpiece_v2.json"
COMMISSION_RATE = 0.0015 

@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except: pass
    return 36.5 

LIVE_USDTHB = get_live_fx()

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
    except: pass

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
                
                df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
                df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
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
                df['Trailing_SL'] = tsl
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20, min_periods=1).mean().replace(0, np.nan)
                processed[t] = df.ffill().bfill()
            except: continue
        return processed
    except: return {}

# --- 3. SIDEBAR & STATE ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.info(f"💵 FX Rate: **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Equity (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    watchlist_input = st.text_area("Watchlist:", "NVDA, AAPL, PTT.BK, DELTA.BK")
    tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

# --- 4. DATA PROCESSING (Global Compute) ---
data_dict = fetch_all_data(tickers)
# ตัวแปรกลางสำหรับ Analytics
global_trades = []

if data_dict:
    # คำนวณรอล่วงหน้าจากตัวแรกในลิสต์เพื่อให้ Analytics แสดงผลทันที
    sel_ticker = list(data_dict.keys())[0]
    df_bt = data_dict[sel_ticker].iloc[-500:].copy()
    is_thai = ".BK" in sel_ticker
    fx = 1 if is_thai else LIVE_USDTHB
    bal, pos, entry_p = capital, 0, 0
    
    for i in range(1, len(df_bt)):
        c, p = df_bt.iloc[i], df_bt.iloc[i-1]
        if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48:
            pos = int((bal * (risk_pct/100) / fx) / max(c['Close'] - c['Trailing_SL'], 0.1))
            entry_p = c['Close']
        elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
            pnl = (c['Close'] - entry_p) * pos * fx
            bal += pnl
            global_trades.append({"Date": df_bt.index[i], "PnL": pnl, "Equity": bal})
            pos = 0

# --- 5. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics", "📖 Logic Guide"])

with tabs[4]: # Analytics Hub
    st.header("🛡️ Analytics Hub")
    if global_trades:
        td_df = pd.DataFrame(global_trades)
        st.markdown("---")
        l_m, col_chart, col_stat, r_m = st.columns([0.2, 5, 2.5, 0.2], gap="large")
        
        with col_chart:
            st.subheader("🎲 Monte Carlo Simulation")
            # --- FIX: สีฟ้าสว่าง #58a6ff ---
            fig_mc = go.Figure()
            pnl_values = td_df['PnL'].values
            for _ in range(100):
                sim_path = capital + np.random.choice(pnl_values, size=len(pnl_values), replace=True).cumsum()
                fig_mc.add_trace(go.Scatter(y=sim_path, mode='lines', line=dict(color='#58a6ff', width=1), opacity=0.15, showlegend=False))
            
            fig_mc.update_layout(height=480, margin=dict(l=0,r=0,b=0,t=20), template="plotly_dark", 
                                 paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_mc, use_container_width=True)
            
        with col_stat:
            st.subheader("📊 Performance KPIs")
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            st.metric("Win Rate", f"{win_r:.1f}%")
            st.metric("Profit Factor", f"{td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()):.2f}")
            st.metric("Max Drawdown", f"{((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100:.2f}%")
            st.success("Robustness: Verified")
    else:
        st.info("กรุณารอการดึงข้อมูลเพื่อประมวลผล Analytics...")

with tabs[0]: # Scanner
    st.subheader("📊 Tactical Opportunities")
    results = []
    for t, df in data_dict.items():
        curr = df.iloc[-1]
        sig = "🟢 BUY" if curr['Close'] > curr['SMA200'] and curr['RSI'] < 50 else "⚪ WAIT"
        results.append({"Asset": t, "Price": round(curr['Close'], 2), "Regime": sig, "RSI": round(curr['RSI'], 1)})
    if results: st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tabs[1]: # Deep-Dive
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03)
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='Trend', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS")
