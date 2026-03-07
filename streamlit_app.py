import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ กลยุทธ์ประคองพอร์ต (Risk First)
    1. **The 1% Rule:** ห้ามเสียเงินเกิน 1% ของพอร์ตใน 1 ไม้
    2. **Position Sizing:** ซื้อหุ้นจำนวนเท่าไหร่ ให้ดูที่ระยะ Stop Loss
    3. **ATR Stop Loss:** ใช้ความผันผวนจริงของหุ้นเป็นจุดหนี (ดีกว่าใช้ % คงที่)
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro (Stable Version)")
    
    # --- 3. Sidebar: Settings ---
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Selection")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK"])), default=default_assets)
    
    # --- 4. ฟังก์ชันดึงข้อมูล (Quantitative + ATR) ---
    def get_data(ticker, interval, data_period):
        try:
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # Indicators
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            
            # ATR Calculation (Volatility)
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            df['ATR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(14).mean()
            
            # SL/TP based on ATR
            df['SL'] = df['Close'] - (df['ATR'] * 1.5)
            df['TP'] = df['Close'] + (df['ATR'] * 3.0)
            
            return df
        except: return None

    # --- 5. ประมวลผลผลลัพธ์ ---
    results = []
    if selected_assets:
        with st.spinner('กำลังโหลดข้อมูล...'):
            for t in selected_assets:
                df = get_data(t, "1d", "2y") 
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s = l['Close'], l['RSI'], l['SMA200']
                    
                    if p > s and r < 45: act = "🟢 BUY ON DIP"
                    elif r > 75: act = "💰 TAKE PROFIT"
                    elif p < s: act = "🔴 AVOID/EXIT"
                    else: act = "⚪ WAIT"
                    
                    risk_amount = portfolio_size * (risk_per_trade / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_amount / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": act, "Qty to Buy": qty,
                        "StopLoss": round(l['SL'],2), "Target": round(l['TP'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            st.subheader("🎯 สรุปสัญญาณและแผนคุมความเสี่ยง")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- 6. กราฟและเครื่องมือคำนวณ ---
    if results:
        col1, col2 = st.columns([0.6
