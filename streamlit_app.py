import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max | Institutional", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e1e1; }
    .metric-card { background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; }
    .signal-buy { color: #00ffbb; font-weight: bold; }
    .signal-exit { color: #ff4b4b; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE (ATR & QUANT LOGIC) ---
@st.cache_data(ttl=3600)
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        if any(t in ticker for t in ["PTT", "AOT", "KBANK", "CPALL"]) and "." not in ticker: 
            ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # Technical Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean() # เพิ่มจุดตัด Golden Cross
        
        # RSI Wilder's
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # ATR & Risk Management
        high_low = df['High'] - df['Low']
        high_cp = abs(df['High'] - df['Close'].shift())
        low_cp = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # Dynamic Levels
        df['SL'] = df['Close'] - (df['ATR'] * 2)
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2)
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        
        return df
    except: return None

# --- 3. DASHBOARD LAYOUT ---
tab1, tab2, tab3 = st.tabs(["🚀 Real-time Scanner", "📈 Backtest Insights", "🛡️ Risk Manual"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # Sidebar: Portfolio Control
    with st.sidebar:
        st.header("💰 Risk Control")
        portfolio_size = st.number_input("Portfolio Equity (THB):", value=100000)
        risk_per_trade = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0)
        st.divider()
        assets = st.multiselect("Watchlist:", ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK", "GC=F"], default=["NVDA", "BTC-USD"])
        custom = st.text_input("Add Ticker:").upper()
        if custom: assets.append(custom)

    # Calculation & Logic
    results = []
    for t in assets:
        df = get_data(t)
        if df is not None:
            l = df.iloc[-1]
            p, r, s200, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
            
            # Master Signal Logic (The Core)
            if p > s200 and r < 45 and v > va: 
                act = "🟢 STRONG BUY"
            elif r > 70: 
                act = "💰 TAKE PROFIT"
            elif p < s200: 
                act = "🔴 AVOID/EXIT"
            else: 
                act = "⚪ WAIT"

            # Money Management
            risk_amt = portfolio_size * (risk_per_trade / 100)
            sl_dist = p - l['SL']
            qty = int(risk_amt / sl_dist) if sl_dist > 0 else 0
            # Cap at portfolio size
            qty = min(qty, int(portfolio_size/p))

            results.append({
                "Ticker": t, "Price": round(p,2), "Signal": act,
                "RSI": round(r,1), "Qty": qty, "StopLoss": round(l['SL'],2),
                "Target": round(l['TP'],2), "ATR": round(l['ATR'],2)
            })

    if results:
        res_df = pd.DataFrame(results)
        st.dataframe(res_df.sort_values("Signal"), use_container_width=True, hide_index=True)

        # Charts Section
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            sel = st.selectbox("Select Asset to Visualize:", [r['Ticker'] for r in results])
            df_plot = get_data(sel)
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00')), row=1, col=1)
            # ATR Bands Visualization
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close']-(df_plot['ATR']*2), name='ATR Stop', line=dict(color='rgba(255, 75, 75, 0.3)', dash='dot')), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00d1ff')), row=2, col=1)
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📋 Order Plan")
            target = next(item for item in results if item["Ticker"] == sel)
            st.markdown(f"""
            <div class="metric-card">
                <h3>{sel}</h3>
                <p>Status: {target['Signal']}</p>
                <hr>
                <b>Action Plan:</b><br>
                - Buy Amount: {target['Qty']:,} units<br>
                - Capital Required: {(target['Price']*target['Qty']):,.2f}<br>
                - Max Loss: { (portfolio_size * risk_per_trade/100):,.2f}<br>
                <br>
                <b style="color:#ff4b4b">Stop Loss: {target['StopLoss']}</b>
