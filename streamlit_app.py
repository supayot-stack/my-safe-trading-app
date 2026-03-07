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

with tab2:
    st.header("🛡️ ทำไมต้องใช้ ATR Stop Loss?")
    st.write("ATR (Average True Range) คือค่าเฉลี่ยความกว้างของแท่งเทียนในแต่ละวัน:")
    st.markdown("""
    - **หุ้นซิ่ง (Volatility สูง):** ATR จะกว้าง ระบบจะวาง SL ให้ไกลขึ้นเพื่อกันโดนสะบัดหลุด
    - **หุ้นนิ่ง (Volatility ต่ำ):** ATR จะแคบ ระบบจะวาง SL ให้ใกล้ขึ้นเพื่อให้ได้จำนวนหุ้นที่มากขึ้น
    - **สูตรที่ใช้:** `Stop Loss = ราคาปิด - (ATR * 1.5)`
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro + ATR Stop Loss")
    
    # --- 3. Sidebar ---
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    atr_multiplier = st.sidebar.slider("ATR Multiplier (ความกว้าง SL):", 1.0, 3.0, 1.5)
    
    st.sidebar.divider()
    assets = st.sidebar.multiselect("เลือกหุ้น:", 
                                    options=["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK", "PTT.BK", "CPALL.BK"], 
                                    default=["NVDA", "AAPL", "BTC-USD"])

    # --- 4. ฟังก์ชันดึงข้อมูล & คำนวณ ATR ---
    def get_data(ticker):
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # SMA & RSI
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            
            # Volume Analysis
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            
            # ATR Calculation (True Range)
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR'] = df['TR'].rolling(14).mean()
            
            # ATR Based SL/TP
            df['SL_ATR'] = df['Close'] - (df['ATR'] * atr_multiplier)
            df['TP_ATR'] = df['Close'] + (df['ATR'] * (atr_multiplier * 2))
            
            return df
        except: return None

    # --- 5. ประมวลผล ---
    results = []
    if assets:
        for t in assets:
            df = get_data(t)
            if df is not None:
                l = df.iloc[-1]
                p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                
                # Signal
                if p > s and r < 45 and v > va: signal = "🟢 BUY"
                elif r > 75: signal = "💰 PROFIT"
                elif p < s: signal = "🔴 EXIT"
                else: signal = "⚪ WAIT"
                
                # Position Sizing based on ATR
                risk_amt = portfolio_size * (risk_per_trade / 100)
                sl_dist = p - l['SL_ATR']
                qty = int(risk_amt / sl_dist) if sl_dist > 0 else 0
                
                results.append({
                    "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                    "Signal": signal, "Volume OK": "✅" if v > va else "❌",
                    "Qty": qty, "SL (ATR)": round(l['SL_ATR'],2), "TP (ATR)": round(l['TP_ATR'],2)
                })

        if results:
            res_df = pd.DataFrame(results)
            st.subheader("🎯 สรุปสัญญาณและจุดตัดขาดทุนแบบ ATR")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

            # --- 6. กราฟ + Volume ---
            st.divider()
            col1, col2 = st.columns([0.6, 0.4])
            with col1:
                sel = st.selectbox("🔍 วิเคราะห์กราฟ:", [r['Ticker'] for r in results])
                df_p = get_data(sel)
                if df_p is not None:
                    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                        vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
                    
                    # Price & SMA
                    fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')),
