import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Gemini Quant Terminal Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .highlight-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; border-radius: 10px; border: 1px solid #3b82f6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & ENGINE ---
DB_FILE = "portfolio_data.json"
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

@st.cache_data(ttl=1800)
def get_data(ticker):
    try:
        ticker_final = ticker
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF", "PTTEP", "OR", "DELTA", "KTB"]
        if ticker in thai_list: ticker_final = ticker + ".BK"
        
        df = yf.download(ticker_final, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 100: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['Volatility'] = (df['ATR'] / df['Close']) * 100 # % Volatility
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']
        return df.dropna()
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Personal Quant")
    capital = st.number_input("Total Capital (THB):", value=1000000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0)
    st.divider()
    # ขยายลิสต์เพื่อให้ระบบ Auto-Screener มีตัวเลือกคัดกรอง
    default_list = ["NVDA", "AAPL", "TSLA", "MSTR", "BTC-USD", "ETH-USD", "SOL-USD", "GOLD", "PTT", "CPALL", "DELTA", "GULF", "KTB", "ADVANC"]
    watchlist = st.multiselect("Watchlist Pool:", default_list, default=default_list)
    custom = st.text_input("➕ Add Ticker:").upper().strip()
    final_watchlist = list(set(watchlist + ([custom] if custom else [])))

# --- 4. DATA PROCESSING ---
results = []
data_dict = {}
with st.spinner('Scanning Market...'):
    for ticker in final_watchlist:
        df = get_data(ticker)
        if df is not None:
            data_dict[ticker] = df
            l = df.iloc[-1]
            p, r, s200, s50, vr, vola = l['Close'], l['RSI'], l['SMA200'], l['SMA50'], l['Vol_Ratio'], l['Volatility']
            
            # Logic Scoring
            status = "⚪ NEUTRAL"
            if p > s200 and p > s50 and r < 50 and vr > 1.1: status = "🟢 ACCUMULATE"
            elif r > 75: status = "💰 DISTRIBUTION"
            elif p < s200: status = "🔴 BEARISH"
            
            results.append({
                "Asset": ticker, "Price": p, "Regime": status, "RSI": r, 
                "Vol_Ratio": vr, "Volatility": vola, "SMA200": s200
            })

res_df = pd.DataFrame(results)

# --- 5. MAIN TERMINAL ---
t1, t2, t3, t4 = st.tabs(["🏛 Scanner", "🎯 Auto Quant Picks", "📈 Deep-Dive", "💼 Portfolio"])

with t1:
    st.subheader("📊 Market Opportunities")
    st.dataframe(res_df, use_container_width=True, hide_index=True)

with t2:
    st.markdown("<div class='highlight-card'><h2>🎯 AI Autonomous Picks (Real-Time)</h2></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    
    # 1. Momentum King (ราคาแกร่ง RSI ไม่โอเวอร์บอร์ด)
    with c1:
        st.info("🚀 **Momentum Kings**")
        mo_king = res_df[res_df['Regime'] != "🔴 BEARISH"].sort_values('RSI', ascending=False).head(3)
        for _, row in mo_king.iterrows():
            st.write(f"**{row['Asset']}** (RSI: {row['RSI']:.1f})")

    # 2. Volume Surge (เงินไหลเข้าผิดปกติ)
    with c2:
        st.success("🔥 **Volume Surge**")
        vol_surge = res_df.sort_values('Vol_Ratio', ascending=False).head(3)
        for _, row in vol_surge.iterrows():
            st.write(f"**{row['Asset']}** (Vol: {row['Vol_Ratio']:.2f}x)")

    # 3. Practice Zone (หุ้นซิ่งสำหรับฝึก)
    with c3:
        st.warning("⚡ **High Volatility (Practice)**")
        high_vola = res_df.sort_values('Volatility', ascending=False).head(3)
        for _, row in high_vola.iterrows():
            st.write(f"**{row['Asset']}** (Vola: {row['Volatility']:.2f}%)")

    st.divider()
    st.markdown("### 💡 ทำไมต้องดู 3 หมวดนี้?")
    st.write("- **Momentum:** หาหุ้นที่กำลังเป็นผู้ชนะในตลาด\n- **Volume:** ดูว่าสถาบันกำลัง 'เก็บของ' หรือ 'ทิ้งของ'\n- **Volatility:** ใช้ฝึกการวาง Stop Loss และคุมอารมณ์ในสภาวะเหวี่ยงแรง")

with t3:
    if data_dict:
        sel = st.selectbox("Select Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color='gray'), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with t4:
    st.write("ระบบบันทึกพอร์ต (Coming Soon หรือเชื่อมต่อจากโค้ดเดิมได้ทันที)")
