import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="My Personal Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .status-box { padding: 15px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid; }
    .stMetric { background-color: #161b22; padding: 10px; border-radius: 5px; border: 1px solid #30363d; }
    .highlight-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; border-radius: 10px; border: 1px solid #3b82f6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE ENGINE ---
DB_FILE = "portfolio_data.json"
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=1800)
def get_data(ticker):
    try:
        # Thai Stock Auto-suffix
        ticker_final = ticker
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF", "PTTEP", "OR", "DELTA", "GULF", "KTB"]
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
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']
        return df.dropna()
    except: return None

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Personal Quant")
    capital = st.number_input("Total Capital (THB):", value=1000000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 2.0, 1.0, 0.1)
    st.divider()
    watchlist = st.multiselect("Watchlist:", ["NVDA", "BTC-USD", "ETH-USD", "GOLD", "CPALL", "ADVANC"], default=["NVDA", "BTC-USD"])
    custom = st.text_input("➕ Add Ticker (e.g. TSLA):").upper().strip()
    final_watchlist = list(set(watchlist + ([custom] if custom else [])))

# --- 5. DATA PROCESSING ---
results = []
data_dict = {}
for ticker in final_watchlist:
    df = get_data(ticker)
    if df is not None:
        data_dict[ticker] = df
        l = df.iloc[-1]
        p, r, s200, s50, vr = l['Close'], l['RSI'], l['SMA200'], l['SMA50'], l['Vol_Ratio']
        if p > s200 and p > s50 and r < 45 and vr > 1.2: sig = "🟢 ACCUMULATE"
        elif r > 75: sig = "💰 DISTRIBUTION"
        elif p < s200: sig = "🔴 BEARISH"
        else: sig = "⚪ NEUTRAL"
        
        sl_gap = p - l['SL']
        qty = int((capital * risk_pct/100) / sl_gap) if sl_gap > 0 else 0
        results.append({"Asset": ticker, "Price": round(p, 2), "Regime": sig, "RSI": round(r, 1), "Vol-Force": f"{vr:.2f}x", "Target Qty": qty, "Stop-Loss": round(l['SL'], 2)})

# --- 6. MAIN TERMINAL ---
t1, t2, t3, t4, t5 = st.tabs(["🏛 Scanner", "🎯 Quant Picks", "📈 Deep-Dive", "💼 Portfolio", "📖 Guide"])

with t1:
    st.subheader("📊 Market Opportunities")
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with t2:
    st.markdown("<div class='highlight-card'><h2>🎯 Best Assets & Practice Zone (Mar 2026)</h2></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("🌐 **Top Global Tech**")
        st.markdown("- **NVDA**: AI Infrastructure Leader\n- **MSFT**: Enterprise AI Integration\n- **TSLA**: High Volatility Play")
    with col2:
        st.success("🇹🇭 **Top Thai Picks**")
        st.markdown("- **GULF**: Energy & Digital Infrastructure\n- **DELTA**: High Momentum Tech\n- **KTB**: Strong Fund Flow Dividend")
    with col3:
        st.warning("₿ **Top Crypto Assets**")
        st.markdown("- **BTC**: Market Benchmark\n- **SOL**: Fast-growing Ecosystem\n- **LINK**: RWA & Oracle Leader")

    st.divider()
    st.subheader("⚡ 3 หุ้นซิ่งแนะนำสำหรับฝึก (High Volatility Zone)")
    st.write("หุ้นกลุ่มนี้มีการแกว่งตัวสูง เหมาะสำหรับฝึกจับจังหวะ Volume และการวาง Stop-Loss")
    
    practice_stocks = ["TSLA", "MSTR", "KCE"]
    p_cols = st.columns(3)
    for i, p_stock in enumerate(practice_stocks):
        with p_cols[i]:
            st.metric(p_stock, "High Vol", delta="Practice Required")
            if st.button(f"Add {p_stock} to Watchlist"):
                st.info(f"ไปพิมพ์เพิ่ม {p_stock} ในช่อง Add Ticker ด้านซ้ายได้เลย!")

with t3:
    if data_dict:
        sel = st.selectbox("Select Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Stop-Loss', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume'), row=3, col=1)
        fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with t4:
    st.subheader("💼 Portfolio Management")
    # (Portfolio logic as previously built...)
    if st.session_state.my_portfolio:
        st.write(st.session_state.my_portfolio)
    else: st.info("ไม่มีข้อมูลพอร์ต")

with t5:
    st.header("📖 Guide")
    st.write("ใช้หน้า Quant Picks เพื่อค้นหาไอเดีย และใช้หน้า Scanner เพื่อตรวจสอบจุดเข้าเทรด")
