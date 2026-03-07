import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ (คงเดิม) ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .ai-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันเสริมสำหรับ Backtest (Institutional Standard) ---
def run_backtest_engine(df, initial_cap):
    if df is None or len(df) < 20: return 0, 0, 0, [initial_cap]
    # กลยุทธ์: Buy when Price > SMA200 & RSI < 45
    df['Sig'] = (df['Close'] > df['SMA200']) & (df['RSI'] < 45)
    capital, equity_curve, trades, in_pos = initial_cap, [initial_cap], [], False
    entry, sl, tp = 0, 0, 0
    
    for i in range(1, len(df)):
        if not in_pos and df['Sig'].iloc[i]:
            entry, sl, tp, in_pos = df['Close'].iloc[i], df['SL'].iloc[i], df['TP'].iloc[i], True
        elif in_pos:
            curr = df['Close'].iloc[i]
            if curr <= sl or curr >= tp:
                ret = (curr / entry) - 1
                capital *= (1 + ret)
                trades.append(ret)
                in_pos = False
        equity_curve.append(capital)
    
    wr = (len([r for r in trades if r > 0]) / len(trades) * 100) if trades else 0
    pos_sum = sum([r for r in trades if r > 0])
    neg_sum = abs(sum([r for r in trades if r < 0]))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else 0
    mdd = (pd.Series(equity_curve) / pd.Series(equity_curve).cummax() - 1).min() * 100
    return wr, pf, mdd, equity_curve

# --- 3. ฟังก์ชันดึงข้อมูล (คงเดิม + แก้ไข MultiIndex) ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_tickers and "." not in ticker: ticker += ".BK"
        df = yf.download(ticker, period="2y", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14).mean()
        loss = -delta.where(delta < 0, 0).ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        tr = pd.concat([(df['High']-df['Low']), abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2)
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2)
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        return df
    except: return None

# --- 4. ส่วนหน้าจอหลัก ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% และ ATR Stop Loss")
    st.markdown("""
    ### 🛡️ ทำไมต้องใช้ ATR (Average True Range)?
    * **หุ้นซิ่ง:** ต้องวาง Stop Loss ให้กว้าง (2xATR) เพื่อกันโดนสะบัดหลุด
    * **หุ้นนิ่ง:** วาง Stop Loss ให้แคบลงเพื่อเพิ่มจำนวนหุ้น (Position Size)
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + Analytics")
    
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK", "GC=F"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list: final_list.append(custom_ticker)

    results, corr_data = [], {}
    if final_list:
        with st.spinner('กำลังประมวลผล...'):
            for t in final_list:
                df = get_data(t)
                if df is not None:
                    corr_data[t] = df['Close']
                    l = df.iloc[-1]
                    # Signal Logic
                    if l['Close'] > l['SMA200'] and l['RSI'] < 45 and l['Volume'] > l['Vol_Avg5']: act = "🟢 STRONG BUY"
                    elif l['RSI'] > 70: act = "💰 PROFIT"
                    elif l['Close'] < l['SMA200']: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    qty = int((portfolio_size * risk_per_trade / 100) / (l['Close'] - l['SL'])) if (l['Close'] - l['SL']) > 0 else 0
                    results.append({"Ticker": t, "Price": round(l['Close'],2), "RSI": round(l['RSI'],1), "Signal": act, "Qty": qty, "SL": round(l['SL'],2), "TP": round(l['TP'],2)})

        if results:
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

    st.divider()

    # --- ส่วนวิเคราะห์รายตัว ---
    col1, col2 = st.columns([0.6, 0.4])
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot)
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name
