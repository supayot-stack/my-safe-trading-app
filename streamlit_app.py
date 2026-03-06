import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- ตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="Safe Heaven Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner (Pro Version)")

# --- แถบเมนูด้านข้าง ---
st.sidebar.header("⚙️ การตั้งค่า")
assets = st.sidebar.multiselect("เลือกสินทรัพย์ที่ต้องการติดตาม:", 
                               ["BTC-USD", "ETH-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"],
                               default=["BTC-USD", "GC=F", "NVDA"])

tf = st.sidebar.selectbox("เลือกช่วงเวลา (Timeframe):", ["1d", "1wk", "1h"], index=0)

# --- ฟังก์ชันคำนวณ ---
def calculate_indicators(df):
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=600)
def get_data(tickers, timeframe):
    results = []
    for ticker in tickers:
        df = yf.download(ticker, period="2y", interval=timeframe, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        # กฎสัญญาณ
        trend = "📈 Up Trend" if last['Close'] > last['SMA200'] else "📉 Down Trend"
        if trend == "📈 Up Trend" and last['RSI'] < 40: action = "🟢 STRONG BUY"
        elif last['RSI'] > 75: action = "💰 TAKE PROFIT"
        elif trend == "📉 Down Trend": action = "🔴 AVOID"
        else: action = "Wait"
        
        results.append({
            "Ticker": ticker, 
            "Price": f"{last['Close']:,.2f}",
            "RSI": round(float(last['RSI']), 2),
            "Trend": trend,
            "Action": action
        })
    return pd.DataFrame(results)

# --- ส่วนการแสดงผล ---
if assets:
    # 1. สรุปภาพรวมแบบ Metric Cards
    summary = get_data(assets, tf)
    cols = st.columns(len(assets))
    for i, row in enumerate(summary.to_dict('records')):
        with cols[i]:
            st.metric(row['Ticker'], row['Price'], row['Action'])

    # 2. ตารางสัญญาณไฮไลท์สี
    st.subheader("📊 ตารางวิเคราะห์สัญญาณ")
    def highlight_action(val):
        if 'BUY' in val: color = '#d4edda' # เขียว
        elif 'AVOID' in val: color = '#f8d7da' # แดง
        elif 'PROFIT' in val: color = '#fff3cd' # เหลือง
        else: color = 'white'
        return f'background-color: {color}'
    
    st.dataframe(summary.style.applymap(highlight_action, subset=['Action']), use_container_width=True)

    # 3. กราฟ Interactive
    st.divider()
    selected_asset = st.selectbox("🔍 เจาะลึกกราฟรายตัว:", assets)
    df_plot = yf.download(selected_asset, period="1y", interval=tf, auto_adjust=True)
    if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
    df_plot = calculate_indicators(df_plot)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA200', line=dict(color='orange')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='purple')), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
    fig.update_layout(height=700, template="plotly_white", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("กรุณาเลือกหุ้นหรือคริปโตที่เมนูด้านข้างครับ")
