import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอและสไตล์ (คงเดิม) ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #1e222d; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-top: 10px; border: 1px solid #30363d; }
    .metric-card { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันดึงข้อมูล (คง Logic ATR + RSI ของคุณไว้) ---
@st.cache_data(ttl=3600)
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        # จัดการชื่อหุ้นไทยอัตโนมัติ
        thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_tickers and "." not in ticker: 
            ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        
        # 1. SMA 200 (ตัวกรองเทรนด์หลัก)
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # 2. Standard RSI (Wilder's Smoothing)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # 3. ATR (Average True Range)
        high_low = df['High'] - df['Low']
        high_cp = abs(df['High'] - df['Close'].shift())
        low_cp = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # 4. Dynamic Risk Levels (2xATR)
        df['SL'] = df['Close'] - (df['ATR'] * 2) 
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2) # RR 1:2
        
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        return df
    except:
        return None

# --- 3. ส่วนแสดงผล (Tabs) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% และ ATR Stop Loss")
    st.markdown("""
    ### 🛡️ ทำไมต้องใช้ ATR (Average True Range)?
    * **หุ้นซิ่ง:** Stop Loss กว้างขึ้น ป้องกันโดนสะบัดหลุด
    * **หุ้นนิ่ง:** Stop Loss แคบลง เพื่อเพิ่ม Position Size (ซื้อได้เยอะขึ้นในความเสี่ยงเท่าเดิม)
    * *เราใช้ค่า 2xATR เพื่อเป็นเกราะป้องกันการแกว่งตัวปกติของราคา*
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # Sidebar: การตั้งค่าพอร์ต
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุน
