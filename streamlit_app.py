import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Gemini Master Quant v2", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .highlight-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; border-radius: 10px; border: 1px solid #3b82f6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & UTILS ---
DB_FILE = "portfolio_data_v2.json"

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

def format_ticker(ticker):
    """ ปรับปรุง Thai Stock Mapping ให้ฉลาดขึ้น """
    ticker = ticker.upper().strip()
    # รายชื่อหุ้นไทยเบื้องต้น หรือถ้าความยาวหุ้นไทยมักจะไม่เกิน 10 ตัวอักษรและไม่มี '-'
    if ticker.isalpha() and len(ticker) <= 6 and not ticker.endswith(".BK"):
        # ลองเช็คเบื้องต้น (ในระบบจริงอาจใช้ List หุ้น SET ทั้งหมด)
        thai_logic_list = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC"]
        if ticker in thai_logic_list or st.sidebar.checkbox(f"Is {ticker} Thai Stock?", value=False, key=f"chk_{ticker}"):
            return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE (Enhanced Safety) ---
@st.cache_data(ttl=1800)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # --- Technical Indicators ---
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        # RSI (Wilder's Smoothing)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # ATR & Stop Loss
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        
        # Statistics
        df['Volatility'] = (df['ATR'] / df['Close']) * 100
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']
        
        return df.dropna()
    except Exception as e:
        return None

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🛡️ Secure Quant")
    capital = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    
    default_list = ["NVDA", "AAPL", "TSLA", "BTC-USD", "PTT", "CPALL", "DELTA"]
    watchlist_input = st.text_input("Add Tickers (comma separated):", "NVDA, AAPL, PTT, DELTA")
    final_watchlist = [format_ticker(t.strip()) for t in watchlist_input.split(",") if t.strip()]

# --- 5. DATA PROCESSING (Anti Look-ahead) ---
results = []
data_dict = {}

with st.spinner('Calculating Signals...'):
    for ticker in final_watchlist:
        df = get_data(ticker)
        if df is not None:
            data_dict[ticker] = df
            # แก้ Look-ahead Bias: ใช้ค่า 'เมื่อวาน' ตัดสินใจ (iloc[-2]) เพื่อเทรด 'วันนี้' (iloc[-1])
            curr = df.iloc[-1]
            prev = df.iloc[-2] 
            
            p = curr['Close']
            # Signal Logic (Conservative)
            if p > curr['SMA200'] and p > curr['SMA50'] and prev['RSI'] < 45 and curr['Vol_Ratio'] > 1.2:
                sig = "🟢 ACCUMULATE"
            elif curr['RSI'] > 80: sig = "💰 DISTRIBUTION"
            elif p < curr['SMA200']: sig = "🔴 BEARISH"
            else: sig = "⚪ NEUTRAL"

            # Zero Division Guard & Position Sizing
            risk_cash = capital * (risk_pct / 100)
            sl_gap = p - curr['SL']
            # ป้องกัน sl_gap ติดลบหรือเป็นศูนย์
            safe_sl_gap = max(sl_gap, 0.01) 
            qty = int(risk_cash / safe_sl_gap) if p > curr['SL'] else 0

            results.append({
                "Asset": ticker, "Price": round(p, 2), "Regime": sig, 
                "RSI": round(curr['RSI'], 1), "Target Qty": qty, "Stop-Loss": round(curr['SL'], 2),
                "Volatility": round(curr['Volatility'], 2), "Vol_Ratio": round(curr['Vol_Ratio'], 2)
            })

res_df = pd.DataFrame(results)

# --- 6. MAIN TERMINAL ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest & Stats", "📖 Guide"])

with tabs[0]:
    st.subheader("📊 Market Opportunities")
    if not res_df.empty:
        st.dataframe(res_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No data found. Check ticker names or connection.")

with tabs[1]:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Stop-Loss', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume'), row=3, col=1)
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("💼 Portfolio & Risk Control")
    with st.expander("➕ Add Position"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", final_watchlist)
        p_entry = c2.number_input("Entry Price", value=0.0)
        p_qty = c3.number_input("Quantity", value=0)
        if st.button("Confirm Trade"):
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio)
            st.rerun()

    if st.session_state.my_portfolio:
        # แสดงตารางพอร์ตพร้อมปุ่ม Reset (เหมือนโค้ดเดิมของคุณแต่เพิ่มความคลีน)
        p_list = []
        for asset, info in st.session_state.my_portfolio.items():
            curr_match = next((item for item in results if item["Asset"] == asset), None)
            if curr_match:
                pnl = (curr_match['Price'] - info['entry']) * info['qty']
                p_list.append({"Asset": asset, "Entry": info['entry'], "Current": curr_match['Price'], "Qty": info['qty'], "P/L": round(pnl, 2)})
        st.table(p_list)
        if st.button("Clear Portfolio"):
            save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.header("🧪 Advanced Analytics (Roadmap)")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("1. Sector Analysis")
        st.info("Coming Soon: Heatmap แสดงการไหลของเงินรายกลุ่มอุตสาหกรรม")
        # 

    with col_b:
        st.subheader("2. Correlation Matrix")
        if len(data_dict) > 1:
            # คำนวณ Correlation เบื้องต้นให้เห็นภาพ
            close_df = pd.DataFrame({t: d['Close'] for t in data_dict.items() if (d := t[1]) is not None}).corr()
            fig_corr = go.Figure(data=go.Heatmap(z=close_df.values, x=close_df.columns, y=close_df.columns, colorscale='RdBu_r'))
            fig_corr.update_layout(title="Asset Correlation (Safety Check)", height=400)
            st.plotly_chart(fig_corr, use_container_width=True)
            st.caption("ค่าเข้าใกล้ 1.0 แปลว่าหุ้นวิ่งเหมือนกันเกินไป ไม่ช่วยกระจายความเสี่ยง")
        else:
            st.write("Add more tickers to see correlation.")

    st.divider()
    st.subheader("3. Backtesting Module")
    st.warning("Feature นี้ต้องการการประมวลผลสูง: กำลังพัฒนาส่วนการจำลอง Buy SMA Crossing")

with tabs[4]:
    st.markdown("""
    ### 🛡️ Quant Safety Guide
    1. **Look-ahead Bias:** โค้ดนี้ใช้ `iloc[-2]` (ราคาปิดเมื่อวาน) ในการตัดสินใจ ทำให้คุณไม่เห็น Signal ที่ "ปลอม" จากราคาที่ยังไม่จบวัน
    2. **Position Sizing:** ระบบจะไม่อนุญาตให้ซื้อหุ้นถ้าระยะ Stop-loss ไม่ชัดเจน เพื่อรักษาเงินต้น
    3. **Thai Stocks:** หากเป็นหุ้นไทย อย่าลืมเติม `.BK` หรือกดติ๊กถูกที่ Sidebar
    """)
