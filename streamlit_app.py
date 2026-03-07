import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { 
        background-color: #161b22; padding: 20px; border-radius: 12px; 
        border: 1px solid #30363d; border-left: 5px solid #00ff00;
    }
    div[data-testid="stMetricValue"] { color: #00ff00 !important; font-family: 'Courier New', monospace; }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=3600)
def get_fx():
    try:
        d = yf.download("USDTHB=X", period="1d", progress=False)
        return float(d['Close'].iloc[-1]) if not d.empty else 36.5
    except: return 36.5

LIVE_USDTHB = get_fx()

@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    raw = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
    processed = {}
    for t in tickers:
        try:
            df = raw.xs(t, axis=1, level=1).copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
            if df.empty or len(df) < 200: continue
            
            # --- COMPLETE INDICATORS ---
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            df['TSL'] = df['Close'] - (df['ATR'] * 2.5)
            # Volume Ratio (Current Vol vs 20-Day Avg)
            df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
            processed[t] = df.ffill().dropna()
        except: continue
    return processed

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🏆 THE MASTERPIECE")
    capital = st.number_input("Total Equity (THB)", value=1000000)
    risk_pct = st.slider("Risk (%)", 0.1, 5.0, 1.0)
    watchlist = st.text_area("Watchlist:", "NVDA, AAPL, PTT.BK, DELTA.BK")
    tickers = [t.strip().upper() for t in watchlist.split(",") if t.strip()]

# --- 4. PRE-COMPUTE ANALYTICS ---
data_dict = fetch_all_data(tickers)
global_trades = []

if data_dict:
    # คำนวณรอล่วงหน้าเพื่อ Analytics Hub
    main_t = list(data_dict.keys())[0]
    df_bt = data_dict[main_t].iloc[-500:].copy()
    fx = 1 if ".BK" in main_t else LIVE_USDTHB
    bal, pos, entry_p = capital, 0, 0
    
    for i in range(1, len(df_bt)):
        c, p = df_bt.iloc[i], df_bt.iloc[i-1]
        # COMPLETE ENTRY FORMULA: Trend + RSI Pullback + Volume Spike
        if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48 and c['Vol_Ratio'] > 1.1:
            # Position Sizing Logic
            risk_amt = bal * (risk_pct/100)
            sl_dist = max(c['Close'] - c['TSL'], 0.01)
            raw_qty = (risk_amt / fx) / sl_dist
            pos = int(raw_qty // 100 * 100) if ".BK" in main_t else int(raw_qty)
            entry_p = c['Close']
        elif pos > 0 and (c['Close'] < c['TSL'] or c['RSI'] > 82):
            pnl = (c['Close'] - entry_p) * pos * fx
            bal += pnl
            global_trades.append({"Date": df_bt.index[i], "PnL": pnl, "Equity": bal})
            pos = 0

# --- 5. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "🛡️ Analytics Hub"])

with tabs[0]: # Scanner
    st.subheader("📊 Market Radar (With Volume)")
    scan_res = []
    for t, df in data_dict.items():
        c = df.iloc[-1]; p = df.iloc[-2]
        # Logic check
        is_buy = c['Close'] > c['SMA200'] and p['RSI'] < 50 and c['Vol_Ratio'] > 1.1
        sig = "🟢 ACCUMULATE" if is_buy else "💰 TAKE PROFIT" if c['RSI'] > 80 else "⚪ WAIT"
        
        scan_res.append({
            "Asset": t, "Price": round(c['Close'], 2), 
            "Signal": sig, "RSI": round(c['RSI'], 1), 
            "Vol Ratio": f"{c['Vol_Ratio']:.2f}x", # Volume กลับมาแล้ว
            "Trend": "UP" if c['Close'] > c['SMA200'] else "DOWN"
        })
    st.dataframe(pd.DataFrame(scan_res), use_container_width=True, hide_index=True)

with tabs[1]: # Deep-Dive (With Volume Chart)
    if data_dict:
        sel = st.selectbox("Select Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])
        # Price
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA200', line=dict(color='yellow')), row=1, col=1)
        # RSI
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        # Volume Ratio
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Vol_Ratio'], name='Vol Ratio', marker_color='gray', opacity=0.5), row=3, col=1)
        fig.add_hline(y=1.1, line_dash="dot", line_color="orange", row=3, col=1)
        
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]: # Analytics Hub
    st.header("🛡️ Analytics Hub")
    if global_trades:
        td_df = pd.DataFrame(global_trades)
        c1, c2 = st.columns([5, 2])
        with c1:
            st.subheader("🎲 Monte Carlo Simulation")
            fig_mc = go.Figure()
            # COLOR FIX: #58a6ff
            for _ in range(100):
                sim = capital + np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum()
                fig_mc.add_trace(go.Scatter(y=sim, mode='lines', line=dict(color='#58a6ff', width=1), opacity=0.12, showlegend=False))
            fig_mc.update_layout(height=480, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_mc, use_container_width=True)
        with c2:
            st.subheader("📊 Metrics")
            st.metric("Win Rate", f"{(len(td_df[td_df['PnL']>0])/len(td_df)*100):.1f}%")
            st.metric("Avg P/L", f"{td_df['PnL'].mean():,.0f} ฿")
            st.metric("Max DD", f"{((td_df['Equity']-td_df['Equity'].cummax())/td_df['Equity'].cummax()).min()*100:.1f}%")
    else: st.info("Waiting for Data...")

st.divider(); st.caption("🏆 THE MASTERPIECE | Fully Integrated")
