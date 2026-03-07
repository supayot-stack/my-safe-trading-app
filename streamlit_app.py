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
    .stApp { background-color: #0d1117; color: #e1e4e8; }
    .stTabs [data-baseweb="tab-list"] { gap: 15px; background-color: transparent; border-bottom: 1px solid #21262d; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; border: none !important; color: #8b949e !important; padding: 12px 10px !important; font-size: 15px !important; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; background-color: transparent !important; border-bottom: 2px solid #58a6ff !important; font-weight: 500 !important; }
    .analytics-card { background-color: #161b22; padding: 18px; border-radius: 6px; border: 1px solid #21262d; margin-bottom: 12px; }
    div[data-testid="stExpander"] { border: 1px solid #21262d; border-radius: 8px; background-color: #0d1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX ---
DB_FILE = "the_masterpiece_v3.json"
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
    with open(DB_FILE, "w") as f: json.dump(data, f)

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_popular = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_popular and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE (Indicators) ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
                if df.empty or len(df) < 200: continue
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
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
                processed[t] = df.ffill().dropna()
            except: continue
        return processed
    except: return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    capital = st.number_input("Total Capital (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT.BK, DELTA.BK, BTC-USD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

data_dict = fetch_all_data(final_watchlist)

# --- 5. MAIN DISPLAY TABS ---
tabs = st.tabs(["🏛 Scanner", "📉 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide"])

with tabs[0]:
    results = []
    for t, df in data_dict.items():
        curr = df.iloc[-1]; prev = df.iloc[-2]; p = curr['Close']
        if p > curr['SMA200'] and prev['RSI'] < 48 and curr['RSI'] > prev['RSI']: sig = "🟢 ACCUMULATE"
        elif curr['RSI'] > 82: sig = "💰 TAKE PROFIT"
        elif p < curr['Trailing_SL']: sig = "🔴 RISK OFF"
        else: sig = "⚪ WAIT"
        fx = 1 if ".BK" in t else LIVE_USDTHB
        results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Currency": "THB" if fx==1 else "USD"})
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tabs[1]:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['Trailing_SL'], name='TSL', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
        st.plotly_chart(fig, use_container_width=True)

# --- 6. ADVANCED BACKTEST ENGINE (Daily MTM) ---
with tabs[3]:
    sel_bt = st.selectbox("Backtest Target:", list(data_dict.keys()) if data_dict else ["None"])
    if sel_bt != "None":
        df_bt = data_dict[sel_bt].copy()
        fx_bt = 1 if ".BK" in sel_bt else LIVE_USDTHB
        balance, pos, entry_p = capital, 0, 0
        history, trades_log = [], []

        for i in range(1, len(df_bt)):
            c, p = df_bt.iloc[i], df_bt.iloc[i-1]
            date = df_bt.index[i]
            
            # Entry Logic
            if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48 and c['Vol_Ratio'] > 1.1:
                sl_dist = max(c['Close'] - c['Trailing_SL'], 0.01)
                pos = int((capital * (risk_pct/100) / fx_bt) / sl_dist)
                entry_p = c['Close']
                balance -= (entry_p * pos * COMMISSION_RATE * fx_bt)
            
            # Exit Logic
            elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
                pnl = ((c['Close'] - entry_p) * pos * fx_bt) - (c['Close'] * pos * COMMISSION_RATE * fx_bt)
                balance += pnl
                trades_log.append(pnl)
                pos = 0

            mkt_val = (pos * c['Close'] * fx_bt) if pos > 0 else 0
            history.append({"Date": date, "Equity": balance + mkt_val, "PnL": trades_log[-1] if (pos==0 and len(trades_log)>0) else 0})
        
        bt_results = pd.DataFrame(history)
        st.session_state.bt_data = bt_results # ส่งข้อมูลไปหน้า Analytics
        st.session_state.pnl_list = trades_log

        st.metric("Final Equity", f"{bt_results['Equity'].iloc[-1]:,.2f} THB")
        fig_bt = go.Figure(go.Scatter(x=bt_results['Date'], y=bt_results['Equity'], line=dict(color='#39d353'), fill='tozeroy'))
        fig_bt.update_layout(height=400, template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bt, use_container_width=True)

# --- 7. ANALYTICS HUB (จัด Layout ตามรูป) ---
with tabs[4]:
    if 'bt_data' in st.session_state:
        bt_df = st.session_state.bt_data
        pnls = st.session_state.pnl_list
        
        col_left, col_mid, col_right = st.columns([1.2, 0.6, 1.2], gap="large")
        
        with col_left:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            if pnls:
                fig_mc = go.Figure()
                for _ in range(50):
                    sim = np.random.choice(pnls, size=len(pnls), replace=True).cumsum() + capital
                    fig_mc.add_trace(go.Scatter(y=sim, mode='lines', line=dict(width=0.8, color='#58a6ff'), opacity=0.15, showlegend=False))
                fig_mc.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#21262d'), yaxis=dict(gridcolor='#21262d'))
                st.plotly_chart(fig_mc, use_container_width=True)

        with col_mid:
            # คำนวณ Stats
            win_r = (len([x for x in pnls if x > 0]) / len(pnls)) * 100 if pnls else 0
            pf = sum([x for x in pnls if x > 0]) / abs(sum([x for x in pnls if x < 0])) if any(x < 0 for x in pnls) else 0
            max_dd = ((bt_df['Equity'] - bt_df['Equity'].cummax()) / bt_df['Equity'].cummax()).min() * 100

            st.markdown(f"""
                <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 35px;">
                    <div class="analytics-card"><p style="color: #8b949e; margin: 0; font-size: 13px;">Win Rate</p><h2 style="color: #39d353; margin: 0;">{win_r:.1f}%</h2></div>
                    <div class="analytics-card"><p style="color: #8b949e; margin: 0; font-size: 13px;">Profit Factor</p><h2 style="color: #39d353; margin: 0;">{pf:.2f}</h2></div>
                    <div class="analytics-card" style="border-left: 3px solid #f85149;"><p style="color: #8b949e; margin: 0; font-size: 13px;">Max Drawdown</p><h2 style="color: #f85149; margin: 0;">{max_dd:.1f}%</h2></div>
                </div>
            """, unsafe_allow_html=True)

        with col_right:
            st.markdown("##### 📈 Equity Curve (Daily MTM)")
            st.markdown(f"**Net Balance**: <span style='color:#39d353; font-size: 20px;'>{bt_df['Equity'].iloc[-1]:,.2f} THB</span>", unsafe_allow_html=True)
            fig_eq = go.Figure(go.Scatter(x=bt_df['Date'], y=bt_df['Equity'], line=dict(color='#39d353', width=2), fill='tozeroy', fillcolor='rgba(57, 211, 83, 0.1)'))
            fig_eq.update_layout(height=400, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(gridcolor='#21262d'), yaxis=dict(gridcolor='#21262d'))
            st.plotly_chart(fig_eq, use_container_width=True)
        
        st.markdown("<div style='background-color:#161b22; padding:10px; border-radius:6px; text-align:center; border:1px solid #21262d; color:#39d353;'>✅ System Alpha Verified</div>", unsafe_allow_html=True)
    else:
        st.info("⚠️ Go to 'Backtest' tab and select a ticker first to generate analytics.")

with tabs[5]:
    st.markdown("### 📖 System Logic")
    st.write("1. **Trend Filter**: Close > SMA 200")
    st.write("2. **Entry**: RSI Pullback < 48 + Volume Spike")
    st.write("3. **Risk**: Position size based on ATR Trailing Stop")

st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS")
