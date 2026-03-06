import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import plotly.graph_objects as go

# --- หน้าตา App ---
st.set_page_config(page_title="Safe Heaven App", layout="wide")
st.title("🛡️ Safe Heaven Scanner (Private)")

# รายชื่อที่สแกน
assets = ["BTC-USD", "ETH-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"]

@st.cache_data(ttl=3600) # ช่วยให้แอปโหลดเร็วขึ้น ไม่ดึงข้อมูลซ้ำบ่อยๆ
def get_data():
    results = []
    for ticker in assets:
        df = yf.download(ticker, start="2024-01-01", auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['SMA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        last = df.iloc[-1]
        
        # กฎความปลอดภัย
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

# ส่วนแสดงผลตารางสรุป
st.subheader("📊 ตารางสรุปสัญญาณปัจจุบัน")
summary = get_data()
st.dataframe(summary.style.applymap(lambda x: 'color: green' if 'BUY' in str(x) else ('color: red' if 'EXIT' in str(x) else ''), subset=['Action']))

# ส่วนแสดงกราฟรายตัว
st.divider()
selected = st.selectbox("เลือกดูรายละเอียดกราฟ:", assets)
df_chart = yf.download(selected, start="2024-06-01")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['Close'], name='Price'))
st.plotly_chart(fig, use_container_width=True)
