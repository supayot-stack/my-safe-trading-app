import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING ---
st.set_page_config(page_title="Safe Heaven Quant Pro ATR", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & ATR", "📖 คู่มือเทคนิค"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro + ATR")
    
    # --- 3. Sidebar: Settings & Asset Management ---
    st.sidebar.header("💰 Portfolio Settings")
    p_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    r_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    atr_mult = st.sidebar.slider("ATR Multiplier:", 1.0, 3.0, 1.5)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    
    # ส่วนเลือกหุ้นจากลิสต์
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกจากหุ้นแนะนำ:", 
                                            options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK"])), 
                                            default=default_assets)
    
    # --- จุดที่เพิ่มกลับมา: ส่วนเพิ่มหุ้นเอง ---
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ (เช่น PTT.BK, GC=F):").upper().strip()
    
    # รวมลิสต์หุ้นทั้งหมด
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    # --- 4. ฟังก์ชันดึงข้อมูล & คำนวณ ATR ---
    def get_data(ticker):
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['Vol_Avg'] = df['Volume'].rolling(5).mean()
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            
            # ATR
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            df['SL'] = df['Close'] - (df['ATR'] * atr_mult)
            df['TP'] = df['Close'] + (df['ATR'] * (atr_mult * 2))
            return df
        except: return None

    # --- 5. ประมวลผล ---
    results = []
    if final_list:
        with st.spinner('กำลังประมวลผล...'):
            for
