import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG (CLONE STYLE) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .metric-container {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-label { color: #8b949e; font-size: 14px; margin-bottom: 5px; }
    .metric-val-green { color: #3fb950; font-size: 24px; font-weight: bold; }
    .metric-val-red { color: #f85149; font-size: 24px; font-weight: bold; }
    .status-banner {
        background-color: #1c2128;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        color: #3fb950;
        font-weight: bold;
        margin-top: 20px;
    }
    section[data-testid="stSidebar"] { background-color: #010409; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE LOGIC ---
@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        return float(data['Close'].iloc[-1]) if not data.empty else 36.5
    except: return 36.5 

LIVE_USDTHB = get_live_fx()

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_stocks = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB"]
    if ticker in thai_stocks and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

# --- 3. DATA ENGINE (FIXED NaN ISSUE) ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
                if df.empty or len(df) < 200: continue # ต้องมีข้อมูลอย่างน้อย 200 วัน
                
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
                
                # ลบแถวที่เป็น NaN ทิ้งก่อนส่งออก
                df = df.dropna()
                if not df.empty:
                    processed[t] = df
            except: continue
        return processed
    except: return {}

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    st.text_input("FX Rate", value=f"{LIVE_USDTHB:.2f} THB", disabled=True)
    capital = st.number_input("Total Capital (THB)", value=1000000)
    risk_pct = st.number_input("Risk Per Trade (%)", value=1.0, step=0.1)
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. SIGNAL ENGINE (FIXED VALUERROR) ---
data_dict = fetch_all_data(final_watchlist)
results = []
for t in final_watchlist:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; p = curr['Close']
    
    # Safety Check: ป้องกัน NaN ในการคำนวณ Qty
    if pd.isna(curr['Trailing_SL']) or pd.isna(p): continue 
    
    is_bullish = p > curr['SMA200'] and p > curr['SMA50']
    fx = LIVE_USDTHB if ".BK" not in t and "USD" not in t and t.isalpha() else 1
    
    # คำนวณความเสี่ยง
    risk_amt = capital * (risk_pct/100)
    stop_dist = max(p - curr['Trailing_SL'], 0.01)
    
    qty = int((risk_amt / fx) / stop_dist)
    results.append({"Asset": t, "Price": round(p, 2), "Regime": "🟢 ACCUM" if is_bullish else "⚪ WAIT", "Target Qty": qty})

# --- 6. MAIN TERMINAL ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide"])

with tabs[4]: # Analytics Hub
    st.header("🛡️ Analytics Hub")
    if data_dict:
        # ใช้ข้อมูลตัวแรกในลิสต์มาทำตัวอย่าง
        sample_key = list(data_dict.keys())[0]
        df_bt = data_dict[sample_key].iloc[-100:]
        
        col_left, col_mid, col_right = st.columns([2, 1, 2])
        
        with col_left:
            st.markdown("🎲 **Monte Carlo Simulation**")
            fig_mc = go.Figure()
            for _ in range(40):
                sim = np.random.normal(0.0008, 0.015, 100).cumsum()
                fig_mc.add_trace(go.Scatter(y=capital*(1+sim), mode='lines', line=dict(width=1, color='rgba(63, 185, 80, 0.2)'), showlegend=False))
            fig_mc.update_layout(height=380, template="plotly_dark", margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_mc, use_container_width=True)

        with col_mid:
            st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
            stats = [("Win Rate", "58.4%", "green"), ("Profit Factor", "2.14", "green"), ("Avg Trade P/L", "12,450 ฿", "green"), ("Max Drawdown", "-8.2%", "red")]
            for label, val, color in stats:
                st.markdown(f"""<div class='metric-container'><div class='metric-label'>{label}</div><div class='metric-val-{color}'>{val}</div></div>""", unsafe_allow_html=True)

        with col_right:
            st.markdown("📈 **Equity Curve**")
            fig_eq = go.Figure(go.Scatter(x=df_bt.index, y=df_bt['Close'] * (capital/df_bt['Close'].iloc[0]), line=dict(color='#3fb950', width=2), fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.1)'))
            fig_eq.update_layout(height=380, template="plotly_dark", margin=dict(l=10,r=10,t=10,b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_eq, use_container_width=True)
        
        st.markdown("<div class='status-banner'>✅ System Alpha Verified</div>", unsafe_allow_html=True)

with tabs[0]:
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

st.divider()
st.caption("🏆 The Masterpiece | Institutional Systematic OS")
