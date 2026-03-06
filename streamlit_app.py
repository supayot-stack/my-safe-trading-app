import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Real-time", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner (Real-time Mode)")

# --- 2. แถบเมนูด้านข้าง ---
st.sidebar.header("⚙️ Settings")
assets = st.sidebar.multiselect(
    "เลือกสินทรัพย์ที่ต้องการ:", 
    ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"],
    default=["BTC-USD", "GC=F", "NVDA"]
)

# --- 3. ฟังก์ชันคำนวณและดึงข้อมูล ---
def calculate_indicators(df):
    # SMA 200 (เส้นแบ่งแนวโน้มหลัก)
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=60)
def fetch_scan_data(tickers):
    results = []
    for ticker in tickers:
        try:
            # ดึงข้อมูลรายวันย้อนหลัง 2 ปี เพื่อให้ SMA 200 แม่นยำที่สุด
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 200:
                continue
            
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
        except:
            continue
    return pd.DataFrame(results)

# --- 4. ส่วนการแสดงผล (Main UI) ---
if assets:
    summary_df = fetch_scan_data(assets)
    
    if not summary_df.empty:
        st.subheader("🚀 สัญญาณล่าสุด (อัปเดตอัตโนมัติ)")
        cols = st.columns(len(summary_df))
        
        for i, row in summary_df.iterrows():
            with cols[i]:
                # กำหนดสีตามจังหวะ
                bg_color = "#ffffff"; text_color = "#212529"
                if "BUY" in row['Action']:
