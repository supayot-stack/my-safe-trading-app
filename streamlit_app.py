import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTINGS & STYLE ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #1e222d; padding: 20px; border-radius: 12px; border: 1px solid #30363d; border-left: 5px solid #00ffcc; }
    .status-buy { color: #00ffbb; font-weight: bold; }
    .status-wait { color: #ffcc00; font-weight: bold; }
    .status-exit { color: #ff4b4b; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE (ATR + RSI + SMA + VOLUME) ---
@st.cache_data(ttl=3600)
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        # ระบบจัดการชื่อหุ้นไทยอัตโนมัติ
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB", "BDMS", "GULF"]
        if ticker in thai_list and "." not in ticker: 
            ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        
        # Trend: SMA 200
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # Momentum: RSI (Wilder's)
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # Volatility: ATR (2x for Stop Loss)
        high_low = df['High'] - df['Low']
        high_cp = abs(df['High'] - df['Close'].shift())
        low_cp = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2) 
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2)
        
        # Volume Force: Average 5 days
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        
        return df.dropna(subset=['SMA200', 'ATR'])
    except: return None

# --- 3. SIDEBAR (PORTFOLIO & ADD ASSETS) ---
st.sidebar.header("💰 My Portfolio")
portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (THB):", value=100000, step=1000)
risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)

st.sidebar.divider()
st.sidebar.header("🔍 ค้นหาและสแกน")

# ส่วนเลือกหุ้นจาก List
default_list = ["NVDA", "AAPL", "BTC-USD", "SET50.BK"]
selected_assets = st.sidebar.multiselect("Watchlist หลัก:", default_list, default=default_list)

# ส่วนเพิ่มหุ้นเอง (ที่ถามหา)
custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นเอง (เช่น TSLA, PTT.BK):").upper().strip()

# รวมรายชื่อหุ้นที่จะสแกน
final_assets = list(selected_assets)
if custom_ticker and custom_ticker not in final_assets:
    final_assets.append(custom_ticker)

# --- 4. DASHBOARD LAYOUT ---
tab1, tab2 = st.tabs(["🚀 Quant Scanner & Trading Plan", "📊 Analysis Chart"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    results = []
    if final_assets:
        with st.spinner('กำลังสแกนตลาด...'):
            for t in final_assets:
                df = get_data(t)
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    # --- Signal Logic ---
                    vol_ok = v > va
                    if p > s and r < 45 and vol_ok: act = "🟢 STRONG BUY"
                    elif p > s and r < 45: act
