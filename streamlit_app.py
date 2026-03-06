import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="Safe Heaven Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { border: 1px solid #dee2e6; padding: 10px; border-radius: 10px; background-color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner (Pro v2.0)")

# --- 2. แถบเมนูด้านข้าง (Sidebar) ---
st.sidebar.header("⚙️ Settings")
assets = st.sidebar.multiselect(
    "เลือกสินทรัพย์ที่ต้องการ:", 
    ["BTC-USD", "ETH-USD", "BNB-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"],
    default=["BTC-USD", "GC=F", "NVDA"]
)

tf = st.sidebar.selectbox(
    "เลือกหน่วยเวลา (Timeframe):", 
    options=["1h", "1d", "1wk"], 
    format_func=lambda x: "รายชั่วโมง (1H)" if x=="1h" else ("รายวัน (1D)" if x=="1d" else "รายสัปดาห์ (1W)"),
    index=1
)

# --- 3. ฟังก์ชันคำนวณและดึงข้อมูล ---
def get_optimal_period(timeframe):
    if timeframe == "1h": return "1mo"
    if timeframe == "1d": return "2y"   
    if timeframe == "1wk": return "5y"
    return "2y"

def calculate_indicators(df):
    # SMA 200
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=600)
def fetch_scan_data(tickers, timeframe):
    results = []
    period = get_optimal_period(timeframe)
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval=timeframe, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 200: continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            trend = "📈 Up Trend" if last['Close'] > last['SMA200'] else "📉 Down Trend"
            
            if trend == "📈 Up Trend" and last['RSI'] < 40:
                action = "🟢 STRONG BUY"
            elif last['RSI'] > 75:
                action = "💰 TAKE PROFIT"
            elif trend == "📉 Down Trend":
                action = "🔴 EXIT/AVOID"
            else:
                action = "Wait"
                
            results.append({
                "Ticker": ticker,
                "Price": f"{float(last['Close']):,.2f}",
                "Change %": f"{((float(last['Close']) - float(prev['Close'])) / float(prev['Close']) * 100):.2f}%",
                "RSI": round(float(last['RSI']), 2),
                "Trend": trend,
                "Action": action
            })
        except: continue
    return pd.DataFrame(results)

# --- 4. ส่วนการแสดงผล (Main UI) ---
if assets:
    summary_df = fetch_scan_data(assets, tf)
    
    if not summary_df.empty:
        cols = st.columns(len(summary_df))
        for i, row in summary_df.iterrows():
            with cols[i]:
                st.metric(row['Ticker'], row['Price'], row['Change %'])

        st.subheader("📊 ตารางสรุปสัญญาณปัจจุบัน")
        
        def style_action(val):
            color = 'white'
            if 'BUY' in val: color = '#d4edda'
            elif 'EXIT' in val: color = '#f8d7da'
            elif 'PROFIT' in val: color = '#fff3cd'
            return f'background-color: {color}'

        st.dataframe(summary_df.style.applymap(style_action, subset=['Action']), use_container_width=True)
