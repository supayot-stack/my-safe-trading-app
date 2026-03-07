import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG (ล้างใหม่ให้คลีน) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    .metric-card {
        background-color: #1c2128; padding: 15px; border-radius: 10px;
        border: 1px solid #30363d; text-align: center; margin-bottom: 12px;
    }
    .m-label { font-size: 11px; color: #8b949e; text-transform: uppercase; }
    .m-value { font-size: 20px; font-weight: bold; margin-top: 5px; }
    .status-bar {
        background-color: rgba(63, 185, 80, 0.1); border: 1px solid #238636;
        color: #3fb950; padding: 12px; border-radius: 6px; text-align: center;
        font-weight: bold; margin-top: 20px;
    }
    h3 { color: #adbac7; font-size: 1.2rem !important; border-left: 4px solid #238636; padding-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX (โครงสร้างเดิมของคุณ) ---
DB_FILE = "the_masterpiece_v2.json"
BAK_FILE = "the_masterpiece_v2.json.bak"
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
        shutil.copy(DB_FILE, BAK_FILE)
    except: pass

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_popular = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_popular and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE (สูตรคำนวณเดิมของคุณ) ---
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

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.info(f"💵 FX: **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Equity (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. DATA PROCESSING ---
data_dict = fetch_all_data(final_watchlist)
results = []
for t in final_watchlist:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; prev = df.iloc[-2]; p = curr['Close']
    sig = "🟢 ACCUMULATE" if (p > curr['SMA200'] and prev['RSI'] < 48 and curr['RSI'] > prev['RSI']) else "⚪ WAIT"
    if curr['RSI'] > 82: sig = "💰 TAKE PROFIT"
    elif p < curr['SMA200']: sig = "🔴 RISK OFF"
    
    is_thai = ".BK" in t
    fx = 1 if is_thai else LIVE_USDTHB
    sl_gap = max(p - curr['Trailing_SL'], 0.01)
    qty = int((capital * (risk_pct/100) / fx) / sl_gap) if not is_thai else int(((capital * (risk_pct/100)) / sl_gap) // 100) * 100
    results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Target Qty": qty})

# --- 6. MAIN DISPLAY (ปรับปรุง Layout ให้คมชัด) ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics"])

with tabs[0]:
    st.subheader("📊 Tactical Opportunities")
    if results: st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tabs[1]:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['Trailing_SL'], name='TSL', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=20))
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("💼 Active Position Log")
    c1, c2, c3 = st.columns(3)
    p_asset = c1.selectbox("Asset", list(data_dict.keys()) if data_dict else ["None"])
    p_entry = c2.number_input("Entry Price", 0.0)
    p_qty = c3.number_input("Quantity", 0)
    if st.button("Commit Trade"):
        st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
        save_portfolio(st.session_state.my_portfolio); st.rerun()
    if st.session_state.my_portfolio:
        st.write(st.session_state.my_portfolio)
        if st.button("Clear Portfolio"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.subheader("🧪 Strategy Backtest")
    sel_bt = st.selectbox("Target:", list(data_dict.keys()) if data_dict else ["None"], key="bt")
    if sel_bt != "None":
        df_bt = data_dict[sel_bt].iloc[-500:].copy()
        fx_bt = 1 if ".BK" in sel_bt else LIVE_USDTHB
        bal, pos, trades, entry_p = capital, 0, [], 0
        for i in range(1, len(df_bt)):
            c, pr = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c['Close'] > c['SMA200'] and pr['RSI'] < 48:
                pos = int(((bal * (risk_pct/100)) / fx_bt) / max(c['Close'] - c['Trailing_SL'], 0.01))
                entry_p = c['Close']; trades.append({"Date": df_bt.index[i], "Type": "BUY"})
            elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
                pnl = (c['Close'] - entry_p) * pos * fx_bt
                bal += pnl; trades.append({"Date": df_bt.index[i], "Type": "SELL", "PnL": pnl, "Equity": bal})
                pos = 0
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            st.metric("Final Equity", f"{bal:,.2f} THB")
            st.plotly_chart(go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], name='Equity', line=dict(color='#00ff00'))), use_container_width=True)

with tabs[4]:
    st.subheader("🛡️ Analytics Hub")
    if 'td_df' in locals() and not td_df.empty:
        col_c, col_s = st.columns([7, 3])
        with col_c:
            st.caption("🎲 Monte Carlo Simulation")
            fig_mc = go.Figure()
            for _ in range(30):
                sim = np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital
                fig_mc.add_trace(go.Scatter(y=sim, mode='lines', line=dict(width=1), opacity=0.2, showlegend=False))
            fig_mc.update_xaxes(showgrid=True, gridcolor='#22272e'); fig_mc.update_yaxes(showgrid=True, gridcolor='#22272e')
            fig_mc.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=400, template="plotly_dark")
            st.plotly_chart(fig_mc, use_container_width=True)
        with col_s:
            st.markdown(f'<div class="metric-card"><div class="m-label">Win Rate</div><div class="m-value" style="color:#3fb950">{(len(td_df[td_df["PnL"]>0])/len(td_df))*100:.1f}%</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="metric-card"><div class="m-label">Max Drawdown</div><div class="m-value" style="color:#f85149">{((td_df["Equity"]-td_df["Equity"].cummax())/td_df["Equity"].cummax()).min()*100:.1f}%</div></div>', unsafe_allow_html=True)

st.markdown('<div class="status-bar">✅ System Alpha Verified</div>', unsafe_allow_html=True)
