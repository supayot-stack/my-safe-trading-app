import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- หน้าตา App ---
st.set_page_config(page_title="Safe Heaven App", layout="wide")
st.title("🛡️ Safe Heaven Scanner (Private)")

# รายชื่อที่สแกน
assets = ["BTC-USD", "ETH-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"]

@st.cache_data(ttl=3600)
def get_data():
    results = []
    for ticker in assets:
        df = yf.download(ticker, start="2024-01-01", auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['SMA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        last = df.iloc[-1]
        
        if last['Close'] > last['SMA200']:
            status = "📈 Up Trend"
            action = "🟢 SAFE BUY" if last['RSI'] < 45 else ("💰 TAKE PROFIT" if last['RSI'] > 75 else "Wait")
        else:
            status = "📉 Down Trend"
            action = "🔴 EXIT/AVOID"
            
        results.append({
            "Ticker": ticker, "Price": round(last['Close'], 2),
            "RSI": round(last['RSI'], 2), "Trend": status, "Action": action
        })
    return pd.DataFrame(results)

# ส่วนตารางสรุป
st.subheader("📊 ตารางสรุปสัญญาณปัจจุบัน")
summary = get_data()
st.dataframe(summary, use_container_width=True)

# ส่วนแสดงกราฟรายตัว
st.divider()
selected = st.selectbox("🔍 เลือกดูรายละเอียดกราฟ:", assets)
df_chart = yf.download(selected, start="2024-06-01", auto_adjust=True)
if isinstance(df_chart.columns, pd.MultiIndex): df_chart.columns = df_chart.columns.get_level_values(0)

df_chart['SMA200'] = ta.sma(df_chart['Close'], length=200)
df_chart['RSI'] = ta.rsi(df_chart['Close'], length=14)

# สร้างกราฟ 2 ชั้น (ราคา และ RSI)
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])

# ชั้นบน: ราคา + SMA200
fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['Close'], name='Price', line=dict(color='blue')), row=1, col=1)
fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA200'], name='SMA200', line=dict(color='orange', dash='dot')), row=1, col=1)

# ชั้นล่าง: RSI
fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], name='RSI', line=dict(color='purple')), row=2, col=1)
fig.add_trace(go.Scatter(x=df_chart.index, y=[70]*len(df_chart), name='Overbought', line=dict(color='red', dash='dash')), row=2, col=1)
fig.add_trace(go.Scatter(x=df_chart.index, y=[30]*len(df_chart), name='Oversold', line=dict(color='green', dash='dash')), row=2, col=1)

fig.update_layout(height=600, title_text=f"วิเคราะห์เจาะลึก: {selected}", showlegend=True)
st.plotly_chart(fig, use_container_width=True)
