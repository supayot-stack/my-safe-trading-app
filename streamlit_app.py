import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Institutional Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stat-card { 
        background-color: #161b22; padding: 20px; border-radius: 8px; 
        border: 1px solid #30363d; border-top: 4px solid #58a6ff;
    }
    .signal-acc { color: #3fb950; font-weight: bold; }
    .signal-bear { color: #f85149; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. QUANT ENGINE ---
@st.cache_data(ttl=3600)
def get_institutional_data(ticker):
    try:
        # Smart Thai logic (V7.2)
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper():
            thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF"]
            if ticker in thai_list: ticker += ".BK"

        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        
        # Flatten Multi-Index Columns (Fix for yfinance latest version)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

        # Volatility (ATR)
        tr = pd.concat([
            df['High'] - df['Low'],
            abs(df['High'] - df['Close'].shift()),
            abs(df['Low'] - df['Close'].shift())
        ], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # Levels
        df['SL'] = df['Close'] - (df['ATR'] * 2.5) 
        df['TP'] = df['Close'] + (df['ATR'] * 5.0) 

        # Volume Flow
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']

        return df.dropna()
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Quant Control")
    equity = st.number_input("Total Equity (THB):", value=1000000, step=10000)
    max_risk = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0, 0.1)
    
    st.divider()
    watchlist = st.multiselect("Watchlist:", ["NVDA", "AAPL", "BTC-USD", "SET50.BK", "GOLD"], default=["NVDA", "BTC-USD"])
    custom = st.text_input("➕ Add Ticker:").upper().strip()
    
    final_watchlist = list(watchlist)
    if custom and custom not in final_watchlist: final_watchlist.append(custom)

# --- 4. DATA PROCESSING ---
results = []
data_dict = {}

if final_watchlist:
    with st.spinner('Scanning Assets...'):
        for ticker in final_watchlist:
            df = get_institutional_data(ticker)
            if df is not None:
                data_dict[ticker] = df
                l = df.iloc[-1]
                p, r, s200, s50, vr = l['Close'], l['RSI'], l['SMA200'], l['SMA50'], l['Vol_Ratio']
                
                # Logic: Trend + RSI + Volume
                if p > s200 and p > s50 and r < 45 and vr > 1.2:
                    signal = "🟢 ACCUMULATE"
                elif r > 75: signal = "💰 DISTRIBUTION"
                elif p < s200: signal = "🔴 BEARISH REGIME"
                else: signal = "⚪ NEUTRAL"

                # Position Sizing
                risk_cash = equity * (max_risk / 100)
                sl_gap = p - l['SL']
                qty = int(risk_cash / sl_gap) if sl_gap > 0 else 0
                qty = min(qty, int(equity / p))

                results.append({
                    "Asset": ticker, "Price": round(p, 2), "Regime": signal,
                    "RSI": round(r, 1), "Vol-Force": f"{vr:.2f}x",
                    "Target Qty": f"{qty:,}", "Notional (THB)": f"{(qty*p):,.0f}",
                    "Stop-Loss": round(l['SL'], 2)
                })

# --- 5. MAIN TERMINAL ---
t1, t2 = st.tabs(["🏛 Market Scanner", "📈 Technical Deep-Dive"])

with t1:
    st.subheader("🏛 Institutional Order Flow")
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Equity", f"{equity:,.0f}")
        c2.metric("Risk Budget", f"{(equity*max_risk/100):,.0f}")
        c3.metric("Assets Active", len(results))

with t2:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_plot = data_dict[sel]
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.2, 0.3])
        
        # Price & Indicators
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='yellow', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SL'], name='Institutional SL', line=dict(color='red', dash='dot')), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

        # Volume
        colors = ['green' if c >= o else 'red' for o, c in zip(df_plot['Open'], df_plot['Close'])]
        fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color=colors), row=3, col=1)
        
        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
