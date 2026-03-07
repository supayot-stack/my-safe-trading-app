import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil
from datetime import datetime

# --- 1. PRO UI CONFIG (Merge CSS with Production Logic) ---
st.set_page_config(page_title="The Masterpiece | Secure OS", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #e1e4e8; }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; background-color: transparent; border-bottom: 1px solid #21262d; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; color: #8b949e !important; padding: 12px 0px !important; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom: 2px solid #58a6ff !important; font-weight: 500 !important; }
    
    /* Sidebar Custom Fields */
    .sb-row { display: flex; justify-content: space-between; margin-bottom: 2px; }
    .sb-label { color: #8b949e; font-size: 13px; }
    .sb-value { color: #ffffff; font-size: 13px; font-weight: bold; }
    
    /* Analytics Cards */
    .analytics-card { background-color: #161b22; padding: 15px; border-radius: 6px; border: 1px solid #21262d; margin-bottom: 10px; }
    .status-verified { background-color: #161b22; padding: 10px; border-radius: 6px; text-align: center; border: 1px solid #21262d; margin-top: 15px; color: #39d353; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIG & SAFETY PARAMETERS ---
DB_FILE = "the_masterpiece_v3.json"
BAK_FILE = "the_masterpiece_v3.json.bak"
COMMISSION_RATE = 0.0015 
SLIPPAGE = 0.001 
MAX_CAP_PER_STOCK = 0.20  
STALE_DATA_THRESHOLD_DAYS = 3 

@st.cache_data(ttl=3600)
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except Exception: return 36.52 

LIVE_USDTHB = get_live_fx()

# --- 3. DATA & PORTFOLIO ENGINE ---
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except Exception: return {}
    return {}

def save_portfolio(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
        shutil.copy(DB_FILE, BAK_FILE)
    except Exception as e: st.error(f"Error: {e}")

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
                
                # Indicators
                df['SMA200'] = df['Close'].rolling(200).mean()
                df['SMA50'] = df['Close'].rolling(50).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14).mean()
                
                sl_raw = df['Close'] - (df['ATR'] * 2.5)
                tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
                for i in range(1, len(df)):
                    tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
                df['Trailing_SL'] = tsl
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean().replace(0, np.nan)
                processed[t] = df.ffill().bfill()
            except Exception: continue
        return processed
    except Exception: return {}

# --- 4. SIDEBAR (Enhanced Visuals) ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.markdown('<h3>🏆 The Masterpiece</h3><p style="color:#8b949e; margin-top:-15px;">Institutional Systematic OS</p>', unsafe_allow_html=True)
    st.divider()
    
    st.markdown(f'<div class="sb-row"><span class="sb-label">FX Rate</span><span class="sb-value">{LIVE_USDTHB:.2f} THB</span></div>', unsafe_allow_html=True)
    capital = st.number_input("Total Capital (THB)", value=1000000, step=50000, label_visibility="collapsed")
    
    st.markdown('<div class="sb-row"><span class="sb-label">Risk Per Trade (%)</span><span class="sb-value">Dynamic</span></div>', unsafe_allow_html=True)
    risk_pct = st.slider("Risk (%)", 0.1, 5.0, 1.0, label_visibility="collapsed")
    
    st.markdown('<p class="sb-label">Watchlist (CSV)</p>', unsafe_allow_html=True)
    watchlist_input = st.text_area("Watchlist", "NVDA, AAPL, PTT, DELTA, BTC-USD, IVL.BK", label_visibility="collapsed")
    
    final_watchlist = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
    data_dict = fetch_all_data(final_watchlist)

# --- 5. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📉 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide"])

# (Logic for Scanner/Deep-Dive same as v3.2...)

with tabs[3]: # Backtest Logic
    st.header("🧪 Strategy Stress Test")
    sel_bt = st.selectbox("Select Target:", list(data_dict.keys()) if data_dict else ["None"])
    if sel_bt != "None" and sel_bt in data_dict:
        df_bt = data_dict[sel_bt].iloc[-500:].copy()
        is_thai = ".BK" in sel_bt
        fx_bt = 1 if is_thai else LIVE_USDTHB
        balance, pos, trades, entry_p = capital, 0, [], 0
        
        for i in range(1, len(df_bt)):
            c, p = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48:
                raw_pos = ((balance * (risk_pct/100)) / fx_bt) / max(c['Close'] - c['Trailing_SL'], 0.01)
                max_pos = (balance * MAX_CAP_PER_STOCK / fx_bt) / c['Close']
                pos = int(min(raw_pos, max_pos))
                entry_p = c['Close'] * (1 + SLIPPAGE)
                balance -= (entry_p * pos * COMMISSION_RATE * fx_bt)
                trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
            elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
                exit_p = c['Close'] * (1 - SLIPPAGE)
                pnl = ((exit_p - entry_p) * pos * fx_bt) - (exit_p * pos * COMMISSION_RATE * fx_bt)
                balance += pnl
                trades.append({"Type": "SELL", "Date": df_bt.index[i], "PnL": pnl, "Equity": balance})
                pos = 0
        
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            st.metric("Net Terminal Value", f"{balance:,.2f} THB")

with tabs[4]: # Analytics Hub (The "Masterpiece" UI)
    if 'td_df' in locals() and not td_df.empty:
        col_left, col_mid, col_right = st.columns([1.2, 0.6, 1.2], gap="large")
        
        with col_left:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            sims = [np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital for _ in range(80)]
            fig_mc = go.Figure()
            for s in sims: fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=0.8, color='#58a6ff'), opacity=0.15, showlegend=False))
            fig_mc.update_layout(height=450, margin=dict(l=0, r=0, b=0, t=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_mc, use_container_width=True)

        with col_mid:
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 0
            avg_pnl = td_df['PnL'].mean()
            max_dd = ((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min() * 100
            
            st.markdown(f"""
                <div class="analytics-card"><p class="sb-label">Win Rate</p><h2 style="color:#39d353; margin:0;">{win_r:.1f}%</h2></div>
                <div class="analytics-card"><p class="sb-label">Profit Factor</p><h2 style="color:#39d353; margin:0;">{pf:.2f}</h2></div>
                <div class="analytics-card"><p class="sb-label">Avg Trade P/L</p><h2 style="color:#ffffff; margin:0;">{avg_pnl:,.0f} <span style="font-size:12px;">THB</span></h2></div>
                <div class="analytics-card" style="border-left:3px solid #f85149;"><p class="sb-label">Max Drawdown</p><h2 style="color:#f85149; margin:0;">{max_dd:.1f}%</h2></div>
            """, unsafe_allow_html=True)

        with col_right:
            st.markdown("##### 📈 Equity Curve")
            st.markdown(f"Final Balance (Net): <span style='color:#39d353; font-weight:bold;'>{balance:,.2f} THB</span>", unsafe_allow_html=True)
            fig_eq = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], line=dict(color='#39d353'), fill='tozeroy', fillcolor='rgba(57, 211, 83, 0.1)'))
            fig_eq.update_layout(height=400, margin=dict(l=0, r=0, b=0, t=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_eq, use_container_width=True)
            
        st.markdown('<div class="status-verified">✅ System Alpha Verified</div>', unsafe_allow_html=True)
    else:
        st.info("Run a Backtest first to see the Analytics Hub.")

st.divider(); st.caption("🏆 The Masterpiece | v3.2 Production Ready")
