import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ (Dark Theme) ---
st.set_page_config(page_title="Professional Quant Dashboard", layout="wide")

# ปรับโทนสีหน้าเว็บให้เป็นสีมืดแบบ TradingView
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { color: #00ffcc; }
    .stSelectbox label { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Quant Scanner")

# --- 2. ตั้งค่ารายการหุ้น ---
assets = {
    "🇺🇸 USA": ["^GSPC", "NVDA", "AAPL", "TSLA"],
    "🇹🇭 THAI": ["^SET50.BK", "PTT.BK", "AOT.BK", "KBANK.BK"],
    "₿ CRYPTO": ["BTC-USD", "ETH-USD"]
}
all_list = [item for sublist in assets.values() for item in sublist]

# --- 3. ฟังก์ชันดึงข้อมูลและคำนวณ ---
def get_clean_data(ticker):
    try:
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        if len(df) < 200: return None
        
        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        return df
    except: return None

# --- 4. ตารางสแกนสัญญาณ (Screener Section) ---
st.subheader("🎯 Market Screener (SMA 200 + RSI)")
results = []
for t in all_list:
    data = get_clean_data(t)
    if data is not None:
        last = data.iloc[-1]
        p, r, s = last['Close'], last['RSI'], last['SMA200']
        
        # Logic
        if p > s and r < 40: signal = "🟢 BUY"
        elif r > 75: signal = "💰 PROFIT"
        elif p < s: signal = "🔴 EXIT"
        else: signal = "Wait"
        
        results.append({"Ticker": t, "Price": round(p, 2), "RSI": round(r, 1), "Signal": signal})

# แสดงตารางแบบสวยงาม
df_res = pd.DataFrame(results)
st.dataframe(df_res, use_container_width=True, hide_index=True)

st.divider()

# --- 5. กราฟเทคนิคัลแบบ Dark Mode ---
selected = st.selectbox("🔍 เลือกหุ้นเพื่อวิเคราะห์ละเอียด:", all_list)
df_plot = get_clean_data(selected)

if df_plot is not None:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # แท่งเทียนสีเด่นตัดกับพื้นหลังมืด
    fig.add_trace(go.Candlestick(
        x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'],
        increasing_line_color='#00ffbb', decreasing_line_color='#ff3366', name='Price'
    ), row=1, col=1)
    
    # เส้น SMA 200 สีทอง
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
    
    # RSI สีฟ้าสว่าง
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)

    fig.update_layout(
        height=600, template="plotly_dark", paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)
