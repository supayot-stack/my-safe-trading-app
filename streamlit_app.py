import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Safe Heaven", layout="wide")
st.title("🛡️ Safe Heaven Scanner")

assets = ["BTC-USD", "ETH-USD", "GC=F", "NVDA", "AAPL"]

def calculate_indicators(df):
    # คำนวณ SMA 200
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    # คำนวณ RSI (แบบ Manual)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=3600)
def get_data():
    results = []
    for ticker in assets:
        df = yf.download(ticker, period="2y", auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = calculate_indicators(df)
        last = df.iloc[-1]
        
        status = "📈 Up Trend" if last['Close'] > last['SMA200'] else "📉 Down Trend"
        action = "🟢 BUY" if (status == "📈 Up Trend" and last['RSI'] < 45) else "Wait"
        
        results.append({"Ticker": ticker, "Price": round(float(last['Close']), 2), "RSI": round(float(last['RSI']), 2), "Trend": status, "Action": action})
    return pd.DataFrame(results)

summary = get_data()
st.table(summary) # ใช้ table ธรรมดาเพื่อความชัวร์
