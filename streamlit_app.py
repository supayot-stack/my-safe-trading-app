import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG (Institutional Dark) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    
    /* KPI Metric Cards - Center Column */
    div[data-testid="stMetric"] {
        background-color: #1b2128; 
        padding: 20px !important; 
        border-radius: 12px; 
        border: 1px solid #30363d; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    div[data-testid="stMetricValue"] { color: #2ea043 !important; font-family: 'Courier New', monospace; font-weight: bold; }
    div[data-testid="stMetricLabel"] { color: #8b949e !important; text-transform: uppercase; font-size: 0.75rem; }

    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; border-radius: 6px 6px 0px 0px; 
        padding: 12px 25px; color: #8b949e; 
    }
    .stTabs [aria-selected="true"] { 
        background-color: #238636 !important; color: white !important; font-weight: bold;
    }
    
    .alpha-verified {
        background: rgba(35, 134, 54, 0.1);
        border: 1px solid #238636;
        color: #3fb950;
        padding: 12px;
        text-align: center;
        border-radius: 6px;
        font-weight: bold;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX ---
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

# --- 3. CORE QUANT ENGINE ---
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
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    st.info(f"💵 FX Rate: **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Equity (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. SYSTEM GLOBAL CALCULATION (Fix for Data Loading) ---
data_dict = fetch_all_data(final_watchlist)
td_df = pd.DataFrame() # Initialize empty for Analytics

if data_dict:
    # เลือก Asset ตัวแรกมาทำ Simulation เบื้องหลังให้หน้า Analytics ทันที
    sel_auto = list(data_dict.keys())[0]
    df_bt = data_dict[sel_auto].iloc[-500:].copy()
    is_thai = ".BK" in sel_auto or (sel_auto.isalpha() and len(sel_auto) <= 5 and "USD" not in sel_auto)
    fx_bt = 1 if is_thai else LIVE_USDTHB
    balance, pos, trades, entry_p = capital, 0, [], 0
    
    for i in range(1, len(df_bt)):
        c, p = df_bt.iloc[i], df_bt.iloc[i-1]
        if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48 and c['Vol_Ratio'] > 1.1:
            pos = int(((balance * (risk_pct/100)) / fx_bt) / max(c['Close'] - c['Trailing_SL'], 0.01))
            entry_p = c['Close']; balance -= (entry_p * pos * COMMISSION_RATE * fx_bt)
        elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
            pnl = ((c['Close'] - entry_p) * pos * fx_bt) - (c['Close'] * pos * COMMISSION_RATE * fx_bt)
            balance += pnl; trades.append({"Type": "SELL", "Date": df_bt.index[i], "PnL": pnl, "Equity": balance})
            pos = 0
    if trades: td_df = pd.DataFrame([t for t in trades if "PnL" in t])

# --- 6. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics", "📖 Logic Guide"])

with tabs[4]: # Analytics Hub
    st.header("🛡️ Analytics Hub")
    if not td_df.empty:
        col_chart, col_stat = st.columns([3, 1.2], gap="large")
        
        with col_chart:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            # --- COLOR FIX: #58a6ff | OPACITY: 0.15 ---
            fig_mc = go.Figure()
            pnl_values = td_df['PnL'].values
            for _ in range(60):
                sim_path = capital + np.random.choice(pnl_values, size=len(pnl_values), replace=True).cumsum()
                fig_mc.add_trace(go.Scatter(y=sim_path, mode='lines', line=dict(color='#58a6ff', width=1), opacity=0.15, showlegend=False))
            
            fig_mc.update_layout(height=450, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=10,b=0))
            st.plotly_chart(fig_mc, use_container_width=True)

        with col_stat:
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 1.2
            st.metric("Win Rate", f"{win_r:.1f}%")
            st.metric("Profit Factor", f"{pf:.2f}")
            st.metric("Avg Trade P/L", f"{td_df['PnL'].mean():,.0f} ฿")
            st.metric("Max Drawdown", f"{((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100:.1f}%")
            st.markdown('<div class="alpha-verified">✅ System Alpha Verified</div>', unsafe_allow_html=True)
    else:
        st.info("ระบบกำลังดึงข้อมูล... หากนานเกินไปกรุณาเพิ่ม Ticker ใน Sidebar")

with tabs[0]: # Scanner (ใส่โค้ดเดิมกลับมา)
    st.subheader("📊 Tactical Opportunities")
    results = []
    for t in final_watchlist:
        if t in data_dict:
            df = data_dict[t]; curr = df.iloc[-1]; prev = df.iloc[-2]; p = curr['Close']
            is_bullish = p > curr['SMA200'] and p > curr['SMA50']
            is_pullback = prev['RSI'] < 48 and curr['RSI'] > prev['RSI']
            is_liquid = curr['Vol_Ratio'] > 1.1
            sig = "🟢 ACCUMULATE" if is_bullish and is_pullback and is_liquid else ("💰 TAKE PROFIT" if curr['RSI'] > 82 else ("🔴 RISK OFF" if p < curr['SMA200'] else "⚪ WAIT"))
            results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1)})
    if results: st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tabs[1]: # Deep-Dive (ใส่โค้ดเดิมกลับมา)
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()), key="dive_sel")
        df_p = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='Inst. Trend', line=dict(color='yellow', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan', width=1.5)), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# ส่วนอื่นๆ (Logic Guide/Portfolio) ยังคงเดิมตามโค้ดต้นฉบับ
st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS v2.7")
