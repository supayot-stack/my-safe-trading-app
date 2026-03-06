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
        # ดึงข้อมูลย้อนหลัง 2 ปีเพื่อให้ SMA200 คำนวณได้แม่นยำ
        df = yf.download(ticker, period="2y", auto_adjust=True)
        
        # แก้ปัญหา Multi-index ของ yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if df.empty: continue

        df['SMA200'] = ta.sma(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        last = df.iloc[-1]
        
        # กฎความปลอดภัย
        if last['Close'] > last['SMA200']:
            status = "📈 Up Trend"
            if last['RSI'] < 45: action = "🟢 SAFE BUY"
            elif last['RSI'] > 75: action = "💰 TAKE PROFIT"
            else: action = "Wait"
        else:
            status = "📉 Down Trend"
            action = "🔴 EXIT/AVOID"
            
        results.append({
            "Ticker": ticker, 
            "Price": round(float(last['Close']), 2),
            "RSI": round(float(last['RSI']), 2), 
            "Trend": status, 
            "Action": action
        })
    return pd.DataFrame(results)

# ส่วนตารางสรุป
st.subheader("📊 ตารางสรุปสัญญาณปัจจุบัน")
try:
    summary = get_data()
    st.dataframe(summary, use_container_width=True)
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

# ส่วนแสดงกราฟรายตัว
st.divider()
selected = st.selectbox("🔍 เลือกดูรายละเอียดกราฟ:", assets)

# ดึงข้อมูลมาวาดกราฟ
df_chart = yf.download(selected, period="1y", auto_adjust=True)
if isinstance(df_chart.columns, pd.MultiIndex):
    df_chart.columns = df_chart.columns.get_level_values(0)

df_chart['SMA200'] = ta.sma(df_chart['Close'], length=200)
df_chart['RSI'] = ta.rsi(df_chart['Close'], length=14)

# สร้างกราฟ 2 ชั้น
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                    vertical_spacing=0.1, row_heights=[0.7, 0.3])

# ชั้นบน: ราคา + SMA200
fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['Close'], name='Price', line=dict(color='blue')), row=1, col=1)
fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA200'], name='SMA200', line=dict(color='orange', dash='dot')), row=1, col=1)

# ชั้นล่าง: RSI
fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['RSI'], name='RSI', line=dict(color='purple')), row=2, col=1)
fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

fig.update_layout(height=600, title_text=f"วิเคราะห์เจาะลึก: {selected}", showlegend=True)
st.plotly_chart(fig, use_container_width=True)
