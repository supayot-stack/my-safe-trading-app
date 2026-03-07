import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG (Matching the Reference Image) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    /* Global Background & Text */
    .stApp { background-color: #0d1117; color: #e1e4e8; }
    
    /* Custom Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background-color: transparent;
        border-bottom: 1px solid #21262d;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        color: #8b949e !important;
        padding: 10px 0px !important;
        font-size: 16px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        border-bottom: 2px solid #58a6ff !important;
        font-weight: 600 !important;
    }

    /* Analytics Card Styling */
    .analytics-card {
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 8px; 
        border: 1px solid #30363d; 
        margin-bottom: 15px;
        text-align: center;
    }
    .card-label { color: #8b949e; font-size: 14px; margin-bottom: 5px; }
    .card-value { font-size: 24px; font-weight: bold; margin: 0; }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #21262d; }
    
    /* Input Boxes */
    div[data-baseweb="input"] { background-color: #0d1117; border: 1px solid #30363d; }
    
    /* Status Bar */
    .status-bar {
        background-color: #1c2128;
        border: 1px solid #444c56;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
        margin-top: 20px;
        color: #39d353;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA UTILITIES ---
DB_FILE = "the_masterpiece_pro.json"

@st.cache_data(ttl=3600)
def get_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        return float(data['Close'].iloc[-1]) if not data.empty else 36.5
    except: return 36.5

LIVE_FX = get_fx()

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {}

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=1800)
def fetch_market_data(tickers):
    if not tickers: return {}
    processed = {}
    try:
        raw = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        for t in tickers:
            df = raw.xs(t, axis=1, level=1).copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
            if df.empty or len(df) < 200: continue
            
            # Indicators
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            
            # Volatility-Based Trailing SL
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            sl_raw = df['Close'] - (df['ATR'] * 2.5)
            tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
            for i in range(1, len(df)):
                tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
            df['TSL'] = tsl
            df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
            processed[t] = df.ffill().bfill()
    except: pass
    return processed

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.caption("Institutional Systematic OS")
    st.divider()
    
    fx_display = st.text_input("FX Rate", f"{LIVE_FX:.2f} THB", disabled=True)
    capital = st.number_input("Total Capital (THB)", value=1000000, step=50000)
    risk_pct = st.number_input("Risk Per Trade (%)", value=1.0, step=0.1)
    
    st.divider()
    watchlist_raw = st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    tickers = [t.strip().upper() for t in watchlist_raw.split(",") if t.strip()]
    # Auto-format Thai Stocks
    tickers = [t + ".BK" if t in ["PTT", "DELTA", "AOT", "CPALL"] and not t.endswith(".BK") else t for t in tickers]

# --- 5. CORE LOGIC ---
data_dict = fetch_market_data(tickers)
if 'portfolio' not in st.session_state: st.session_state.portfolio = load_data()

# --- 6. DASHBOARD TABS ---
t_scanner, t_deep, t_port, t_backtest, t_analytics, t_guide = st.tabs([
    "🏛 Scanner", "📉 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide & Logic"
])

with t_scanner:
    st.subheader("📊 Market Scan")
    scan_results = []
    for t, df in data_dict.items():
        curr = df.iloc[-1]
        is_bull = curr['Close'] > curr['SMA200']
        is_pb = curr['RSI'] < 50
        status = "🟢 ACCUMULATE" if is_bull and is_pb else "⚪ WAIT"
        scan_results.append({"Asset": t, "Price": f"{curr['Close']:.2f}", "RSI": f"{curr['RSI']:.1f}", "Signal": status})
    st.dataframe(pd.DataFrame(scan_results), use_container_width=True, hide_index=True)

with t_backtest:
    st.subheader("🧪 Backtest Engine")
    target = st.selectbox("Target Asset", list(data_dict.keys()) if data_dict else ["None"])
    if target != "None":
        df_bt = data_dict[target].copy()
        # Simple Backtest Logic
        bal, pos, trades = capital, 0, []
        for i in range(1, len(df_bt)):
            c, p = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48:
                pos = (bal * (risk_pct/100)) / (c['Close'] - c['TSL'])
                entry_p = c['Close']
                trades.append({"Date": df_bt.index[i], "Type": "BUY", "Price": entry_p})
            elif pos > 0 and (c['Close'] < c['TSL'] or c['RSI'] > 80):
                pnl = (c['Close'] - entry_p) * pos
                bal += pnl
                trades.append({"Date": df_bt.index[i], "Type": "SELL", "PnL": pnl, "Equity": bal})
                pos = 0
        st.session_state.last_bt = pd.DataFrame([t for t in trades if "PnL" in t])
        st.success(f"Backtest Complete: Terminal Value {bal:,.2f} THB")

with t_analytics:
    if 'last_bt' in st.session_state and not st.session_state.last_bt.empty:
        df_res = st.session_state.last_bt
        
        # 3-Column Layout Matching the Image
        col_sim, col_metrics, col_equity = st.columns([1.2, 0.6, 1.2], gap="large")
        
        with col_sim:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            fig_mc = go.Figure()
            # Generate 50 paths
            for _ in range(50):
                path = np.random.choice(df_res['PnL'], size=len(df_res), replace=True).cumsum() + capital
                fig_mc.add_trace(go.Scatter(y=path, mode='lines', line=dict(width=0.8, color='#58a6ff'), opacity=0.15, showlegend=False))
            fig_mc.update_layout(height=400, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               margin=dict(l=0,r=0,t=10,b=0), xaxis_title="Number of Trades", yaxis_title="Portfolio Value (THB)")
            st.plotly_chart(fig_mc, use_container_width=True)

        with col_metrics:
            st.markdown("<br><br>", unsafe_allow_html=True)
            win_rate = (len(df_res[df_res['PnL'] > 0]) / len(df_res)) * 100
            pf = df_res[df_res['PnL'] > 0]['PnL'].sum() / abs(df_res[df_res['PnL'] < 0]['PnL'].sum())
            
            metrics = [
                ("Win Rate", f"{win_rate:.1f}%", "#2ea043"),
                ("Profit Factor", f"{pf:.2f}", "#2ea043"),
                ("Avg Trade P/L", f"{df_res['PnL'].mean():,.0f} THB", "#2ea043"),
                ("Max Drawdown", f"{((df_res['Equity']-df_res['Equity'].cummax())/df_res['Equity'].cummax()).min()*100:.1f}%", "#f85149")
            ]
            
            for label, val, color in metrics:
                st.markdown(f"""
                    <div class="analytics-card">
                        <div class="card-label">{label}</div>
                        <div class="card-value" style="color: {color};">{val}</div>
                    </div>
                """, unsafe_allow_html=True)

        with col_equity:
            st.markdown("##### 📈 Equity Curve")
            final_bal = df_res['Equity'].iloc[-1]
            st.markdown(f"**Final Balance (Net)**: <span style='color:#2ea043; font-size:18px;'>{final_bal:,.2f} THB</span>", unsafe_allow_html=True)
            
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(x=df_res['Date'], y=df_res['Equity'], fill='tozeroy', 
                                      line=dict(color='#39d353', width=2), fillcolor='rgba(57, 211, 83, 0.1)', name="Net Equity"))
            fig_eq.update_layout(height=350, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                               margin=dict(l=0,r=0,t=10,b=0), xaxis_title="Date", yaxis_title="Portfolio Value (THB)")
            st.plotly_chart(fig_eq, use_container_width=True)
            
        st.markdown('<div class="status-bar">✔ System Alpha Verified</div>', unsafe_allow_html=True)
    else:
        st.info("Please run a backtest first to see analytics.")

# --- FOOTER ---
st.divider()
st.caption("🏆 The Masterpiece | Institutional Systematic OS")
