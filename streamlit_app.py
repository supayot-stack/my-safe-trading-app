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
    .signal-buy { color: #3fb950; font-weight: bold; }
    .signal-sell { color: #f85149; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. QUANT ENGINE (Institutional Metrics) ---
@st.cache_data(ttl=3600)
def get_institutional_data(ticker):
    try:
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper(): # Simple Thai logic
            thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB"]
            if ticker in thai_list: ticker += ".BK"

        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # A. Trend & Regime (ADX)
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        # B. Standard RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))

        # C. Volatility Management (ATR & StdDev)
        high_low = df['High'] - df['Low']
        high_cp = abs(df['High'] - df['Close'].shift())
        low_cp = abs(df['Low'] - df['Close'].shift())
        df['TR'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = df['TR'].rolling(14).mean()
        
        # D. Institutional Stop (Chandelier Exit Style)
        df['SL'] = df['Close'] - (df['ATR'] * 2.5) # Wider for institutions
        df['TP'] = df['Close'] + (df['ATR'] * 5.0) # RR 1:2

        # E. Volume Force
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']

        return df.dropna()
    except: return None

# --- 3. SIDEBAR: TERMINAL CONTROL ---
with st.sidebar:
    st.title("🏦 Quant Control")
    st.header("Portfolio Risk")
    equity = st.number_input("Total Equity (THB):", value=1000000, step=10000)
    max_risk = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0, 0.1)
    
    st.divider()
    watchlist = st.multiselect("Active Watchlist:", ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK", "GC=F"], default=["NVDA", "BTC-USD"])
    custom_asset = st.text_input("Add Asset (Ticker):").upper().strip()
    
    final_watchlist = list(watchlist)
    if custom_asset and custom_asset not in final_watchlist: final_watchlist.append(custom_asset)

# --- 4. MAIN TERMINAL ---
t1, t2 = st.tabs(["🏛 Market Scanner", "📈 Technical Deep-Dive"])

results = []
if final_watchlist:
    for ticker in final_watchlist:
        data = get_institutional_data(ticker)
        if data is not None:
            l = data.iloc[-1]
            p, r, s200, s50, vr = l['Close'], l['RSI'], l['SMA200'], l['SMA50'], l['Vol_Ratio']
            
            # Institutional Logic: Trend Confirmation + Momentum + Volume Force
            if p > s200 and p > s50 and r < 45 and vr > 1.2:
                signal = "🟢 ACCUMULATE"
            elif r > 75:
                signal = "💰 DISTRIBUTION"
            elif p < s200:
                signal = "🔴 BEARISH REGIME"
            else:
                signal = "⚪ NEUTRAL"

            # Institutional Position Sizing (Volatility Adjusted)
            risk_cash = equity * (max_risk / 100)
            sl_gap = p - l['SL']
            qty = int(risk_cash / sl_gap) if sl_gap > 0 else 0
            qty = min(qty, int(equity / p))

            results.append({
                "Asset": ticker, "Price": round(p, 2), "Regime": signal,
                "RSI": round(r, 1), "Vol-Force": f"{round(vr, 2)}x",
                "Target Qty": f"{qty:,}", "Notional (THB)": f"{(qty*p):,.0f}",
                "ATR": round(l['ATR'], 2), "Stop-Loss": round(l['SL'], 2)
            })

with t1:
    st.subheader("🏛 Institutional Order Flow & Portfolio Sizing")
    if results:
        res_df = pd.DataFrame(results)
        st.dataframe(res_df, use_container_width=True, hide_index=True)
    
    # Portfolio Summary Logic
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Equity", f"{equity:,.0f} THB")
    with col2:
        st.metric("Risk Budget", f"{(equity*(max_risk/100)):,.0f} THB")
    with col3:
        st.metric("Active Assets", len(results))

with t2:
    if results:
        sel = st.selectbox("Analyze Asset:", [r['Asset'] for r in results])
        df_plot = get_institutional_data(sel)
        
        if df_plot is not None:
            # Bloomberg-Style Charting
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.5, 0.2, 0.3])
            
            # Price & Levels
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA50'], name='SMA 50', line=dict(color='#00ffcc', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SL'], name='Institutional SL', line=dict(color='#f85149', dash='dot')), row=1, col=1)
            
            # RSI
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#58a6ff')), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#f85149", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#3fb950", row=2, col=1)

            # Volume & Flow
            v_color = ['#3fb950' if c >= o else '#f85149' for o, c in zip(df_plot['Open'], df_plot['Close'])]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color=v_color, opacity=0.8), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Vol_Avg20'], name='Avg Vol (20)', line=dict(color='white', width=1)), row=3, col=1)

            fig.update_layout(height=850, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

            # Analysis Insight Box
            target = next(i for i in results if i["Asset"] == sel)
            st.markdown(f"""
            <div class="stat-card">
                <h3>🔍 Institutional Insight: {sel}</h3>
                <p>Market Regime: <b>{target['Regime']}</b> | Volatility Ratio: <b>{target['Vol-Force']}</b></p>
                <hr style="border:0.1px solid #30363d">
                <p>📍 <b>Recommended Entry:</b> Current Price | <b>Position Size:</b> {target['Target Qty']} units</p>
                <p>🛡 <b>Stop-Loss:</b> {target['Stop-Loss']} | 📈 <b>Exp. Target:</b> {df_plot.iloc[-1]['TP']:.2f}</p>
            </div>
            """, unsafe_allow_html=True)

if st.button("🔄 Terminal Sync"): st.rerun()
