import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & ENGINE ---
st.set_page_config(page_title="Pro Quant Terminal", layout="wide")

@st.cache_data(ttl=1800)
def get_clean_data(ticker):
    try:
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicator Calculation
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        
        # Signal Logic
        df['Regime'] = "⚪ NEUTRAL"
        df.loc[(df['Close'] > df['SMA200']) & (df['RSI'] < 45), 'Regime'] = "🟢 ACCUMULATE"
        df.loc[df['RSI'] > 75, 'Regime'] = "💰 DISTRIBUTION"
        df.loc[df['Close'] < df['SMA200'], 'Regime'] = "🔴 BEARISH"
        
        return df.dropna()
    except: return None

# --- 2. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Quant Terminal")
    capital = st.number_input("Total Capital:", value=1000000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0)
    st.divider()
    raw_input = st.text_area("Watchlist (Ticker per line):", "NVDA\nAAPL\nPTT.BK\nBTC-USD")
    watchlist = [t.strip().upper() for t in raw_input.split('\n') if t.strip()]

# --- 3. DATA PROCESSING ---
results, data_dict = [], {}
with st.spinner('Updating Market Data...'):
    for ticker in watchlist:
        df = get_clean_data(ticker)
        if df is not None:
            data_dict[ticker] = df
            last = df.iloc[-1]
            # Risk Management Calculation
            risk_amt = capital * (risk_pct / 100)
            sl_dist = last['Close'] - last['SL']
            qty = int(risk_amt / sl_dist) if sl_dist > 0 else 0
            
            results.append({
                "Asset": ticker, "Price": round(last['Close'], 2), 
                "Regime": last['Regime'], "RSI": round(last['RSI'], 1),
                "Target Qty": qty, "Stop-Loss": round(last['SL'], 2)
            })

# --- 4. MAIN UI (เหลือแค่ Tab ที่ใช้งานจริง) ---
t1, t2, t3 = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio"])

with t1:
    if results:
        res_df = pd.DataFrame(results)
        # ใช้ column_config เพื่อทำให้ UI สวยขึ้นโดยไม่ต้องเขียน CSS เยอะ
        st.dataframe(res_df, use_container_width=True, hide_index=True,
                     column_config={
                         "RSI": st.column_config.ProgressColumn("RSI", min_value=0, max_value=100, format="%.1f"),
                         "Price": st.column_config.NumberColumn(format="$%.2f")
                     })

with t2:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Trailing Stop', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

with t3:
    st.info("ระบบ Portfolio จะเชื่อมต่อกับข้อมูล Scanner อัตโนมัติใน Step ถัดไป")
