import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; color: #ffffff; }
.risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ การทำงานของระบบ"])

with tab2:
    st.header("📖 กฎเหล็กความเสี่ยง 1%")
    st.markdown("ระบบคำนวณจำนวนหุ้นเพื่อจำกัดผลขาดทุนสูงสุดไว้ที่ 1% ของเงินต้นต่อหนึ่งการเทรด")

with tab3:
    st.header("⚙️ System Internal")
    st.info("Logic: SMA200 Trend + RSI Buy on Dip + Silver Volume Filter")

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Assets")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้น:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK"])), default=default_assets)

    def get_data(ticker, interval="1d", data_period="2y"):
        try:
            # แก้ไข Syntax Error: เขียนให้อยู่ในบรรทัดเดียวเพื่อความปลอดภัย
            thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
            if ticker in thai_tickers and "." not in ticker:
                ticker += ".BK"
            
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200:
                return None
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            df['SL'] = df['Close'] * 0.97
            return df
        except:
            return None

    results = []
    if selected_assets:
        with st.spinner('กำลังคำนวณ...'):
            for t in selected_assets:
                df = get_data(t)
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    if p > s and r < 40 and v > va: act = "🟢 STRONG BUY"
                    elif r > 75:
