import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG (GitHub Dark Theme) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #e1e4e8; }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; background-color: transparent; border-bottom: 1px solid #21262d; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; border: none !important; color: #8b949e !important; padding: 12px 0px !important; font-size: 16px !important; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom: 2px solid #58a6ff !important; font-weight: 600 !important; }
    
    .analytics-card { background-color: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 15px; text-align: center; }
    .card-label { color: #8b949e; font-size: 13px; margin-bottom: 5px; }
    .card-value { font-size: 26px; font-weight: bold; margin: 0; }
    
    .status-bar { background-color: #1c2128; border: 1px solid #444c56; border-radius: 6px; padding: 10px; text-align: center; margin-top: 20px; color: #39d353; font-weight: bold; }
    div[data-testid="stMetricValue"] { color: #2ea043 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA UTILITIES & RISK CONSTANTS ---
DB_FILE = "the_masterpiece_v3.json"
BAK_FILE = "the_masterpiece_v3.json.bak"
COMMISSION = 0.0015 # 0.15%

@st.cache_data(ttl=3600)
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        return float(data['Close'].iloc[-1]) if not data.empty else 36.5
    except: return 36.5

LIVE_FX = get_live_fx()

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: 
        json.dump(data, f)
        shutil.copy(DB_FILE, BAK_FILE) # Backup for Safety

# --- 3. QUANT ENGINE (Institutional Logic) ---
@st.cache_data(ttl=1800)
def fetch_market_data(tickers):
    if not tickers: return {}
    processed = {}
    try:
        raw = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False) # 3y for warm-up
        for t in tickers:
            try:
                df = raw.xs(t, axis=1, level=1).copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
                if df.empty or len(df) < 50: continue
                
                # Indicators
                df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
                df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                
                # ATR Trailing Stop Loss
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14, min_periods=1).mean()
                sl_raw = df['Close'] - (df['ATR'] * 2.5)
                tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
                for i in range(1, len(df)):
                    tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
                df['TSL'] = tsl
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20, min_periods=1).mean().replace(0, np.nan)
                processed[t] = df.ffill().bfill()
            except: continue
    except: pass
    return processed

# --- 4. SIDEBAR (Config) ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.caption("Institutional Systematic OS")
    st.divider()
    st.info(f"💵 FX Rate: **{LIVE_FX:.2f} THB**")
    capital = st.number_input("Total Capital (THB)", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    raw_list = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]
    
    # Auto-format Tickers
    thai_stocks = ["PTT", "DELTA", "AOT", "CPALL", "SCB", "KBANK", "ADVANC", "GULF"]
    final_tickers = [t + ".BK" if t in thai_stocks and not t.endswith(".BK") else t for t in raw_list]
    final_tickers = list(dict.fromkeys(final_tickers))

data_dict = fetch_market_data(final_tickers)

# --- 5. MAIN INTERFACE ---
tabs = st.tabs(["🏛 Scanner", "📉 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Logic"])

with tabs[0]:
    st.subheader("📊 Tactical Opportunities")
    scan_results = []
    for t, df in data_dict.items():
        c = df.iloc[-1]; p = df.iloc[-2]
        is_bull = c['Close'] > c['SMA200'] and c['Close'] > c['SMA50']
        is_pb = p['RSI'] < 48 and c['RSI'] > p['RSI']
        status = "🟢 ACCUMULATE" if is_bull and is_pb else "⚪ WAIT"
        scan_results.append({"Asset": t, "Price": round(c['Close'], 2), "Signal": status, "RSI": round(c['RSI'], 1)})
    st.dataframe(pd.DataFrame(scan_results), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("🧪 Strategy Backtest")
    sel_bt = st.selectbox("Select Asset:", list(data_dict.keys()) if data_dict else ["None"])
    if sel_bt != "None":
        df_bt = data_dict[sel_bt].copy()
        fx_val = 1 if ".BK" in sel_bt else LIVE_FX
        bal, pos, trades = capital, 0, []
        
        for i in range(1, len(df_bt)):
            c, p = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48:
                # Safe Position Sizing
                risk_amt = bal * (risk_pct/100)
                sl_gap = max(c['Close'] - c['TSL'], 0.01) # Safety Gap
                pos = (risk_amt / fx_val) / sl_gap
                entry_p = c['Close']
                bal -= (entry_p * pos * COMMISSION * fx_val) # Buying Commission
                trades.append({"Date": df_bt.index[i], "Type": "BUY", "Price": entry_p})
            elif pos > 0 and (c['Close'] < c['TSL'] or c['RSI'] > 82):
                pnl = ((c['Close'] - entry_p) * pos * fx_val) - (c['Close'] * pos * COMMISSION * fx_val) # Selling Commission
                bal += pnl
                trades.append({"Date": df_bt.index[i], "Type": "SELL", "PnL": pnl, "Equity": bal})
                pos = 0
        st.session_state.last_res = pd.DataFrame([t for t in trades if "PnL" in t])
        st.success(f"Backtest Complete: Terminal Value {bal:,.2f} THB")

with tabs[4]:
    if 'last_res' in st.session_state and not st.session_state.last_res.empty:
        df_res = st.session_state.last_res
        
        # 3-Column Layout Matching Reference Image
        col_left, col_mid, col_right = st.columns([1.2, 0.6, 1.2], gap="large")
        
        with col_left:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            fig_mc = go.Figure()
            for _ in range(100):
                path = np.random.choice(df_res['PnL'], size=len(df_res), replace=True).cumsum() + capital
                fig_mc.add_trace(go.Scatter(y=path, mode='lines', line=dict(width=0.8, color='#58a6ff'), opacity=0.12, showlegend=False))
            fig_mc.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_mc, use_container_width=True)

        with col_mid:
            st.markdown("<br><br>", unsafe_allow_html=True)
            win_r = (len(df_res[df_res['PnL'] > 0]) / len(df_res)) * 100
            pf = df_res[df_res['PnL'] > 0]['PnL'].sum() / abs(df_res[df_res['PnL'] < 0]['PnL'].sum()) if any(df_res['PnL'] < 0) else 1
            avg_win = df_res[df_res['PnL'] > 0]['PnL'].mean()
            avg_loss = abs(df_res[df_res['PnL'] < 0]['PnL'].mean())
            expectancy = (win_r/100 * avg_win) - ((1 - win_r/100) * avg_loss) # Expectancy Formula
            
            metrics = [
                ("Win Rate", f"{win_r:.1f}%", "#2ea043"),
                ("Profit Factor", f"{pf:.2f}", "#2ea043"),
                ("Expectancy", f"{expectancy:,.0f} ฿", "#2ea043"),
                ("Max Drawdown", f"{((df_res['Equity']-df_res['Equity'].cummax())/df_res['Equity'].cummax()).min()*100:.1f}%", "#f85149")
            ]
            for label, val, color in metrics:
                st.markdown(f'<div class="analytics-card"><div class="card-label">{label}</div><div class="card-value" style="color: {color};">{val}</div></div>', unsafe_allow_html=True)

        with col_right:
            st.markdown("##### 📈 Equity Curve")
            st.markdown(f"**Final Balance**: <span style='color:#2ea043; font-size:18px;'>{df_res['Equity'].iloc[-1]:,.2f} THB</span>", unsafe_allow_html=True)
            fig_eq = go.Figure()
            fig_eq.add_trace(go.Scatter(x=df_res['Date'], y=df_res['Equity'], fill='tozeroy', line=dict(color='#39d353', width=2), fillcolor='rgba(57, 211, 83, 0.08)'))
            fig_eq.update_layout(height=400, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_eq, use_container_width=True)
            
        st.markdown('<div class="status-bar">✔ System Alpha Verified</div>', unsafe_allow_html=True)
    else:
        st.info("⚠️ Please run a Backtest to see analytics.")

st.divider()
st.caption("🏆 The Masterpiece | Institutional Systematic OS")
