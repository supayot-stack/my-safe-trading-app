import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าสไตล์ (Dark Mode Pro) ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .main-card { 
        background-color: #1e222d; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #30363d; 
        border-left: 5px solid #00ffcc;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันดึงข้อมูลและคำนวณ Indicators ---
@st.cache_data(ttl=3600)
def fetch_and_process(ticker):
    try:
        # ระบบเติม .BK ให้หุ้นไทยอัตโนมัติ
        thai_set = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_set and "." not in ticker: ticker += ".BK"
        
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Trend
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # ATR & Volatility Risk
        high_low = df['High'] - df['Low']
        high_cp = abs(df['High'] - df['Close'].shift())
        low_cp = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # Stop Loss (2xATR) & Take Profit (RR 1:2)
        df['SL'] = df['Close'] - (df['ATR'] * 2)
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2)
        
        # Volume Check
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        
        return df.dropna(subset=['SMA200', 'ATR'])
    except: return None

# --- 3. SIDEBAR: พอร์ตโฟลิโอและรายชื่อหุ้น ---
with st.sidebar:
    st.header("💰 My Portfolio Management")
    capital = st.number_input("เงินทุนทั้งหมด (บาท):", value=100000, step=1000)
    risk_pct = st.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    
    st.divider
