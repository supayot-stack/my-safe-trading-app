import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING & UI ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 20px; border-radius: 12px; border-left: 6px solid #00ffcc; margin-top: 10px; }
    .system-card { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS MANAGEMENT ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & ATR", "📖 คู่มือบริหารความเสี่ยง", "⚙️ กลไกภายใน"])

# --- TAB 2: RISK MANUAL ---
with tab2:
    st.header("📖 กลยุทธ์การคุมความเสี่ยงด้วย ATR")
    st.markdown("""
    ### 🛡️ ทำไมต้อง ATR Stop Loss?
    แทนที่จะใช้เปอร์เซ็นต์คงที่ (เช่น 3%) ระบบนี้ใช้ **ATR (Average True Range)** เพื่อคำนวณความผันผวน:
    * **หุ้นซิ่ง:** ระบบจะวาง Stop Loss ให้กว้างขึ้นเพื่อกันโดนสะบัดหลุด
    * **หุ้นนิ่ง:** ระบบจะวาง Stop Loss ให้แคบลงเพื่อเพิ่มจำนวนหุ้นที่ซื้อได้ (Position Size)
    """)
    

# --- TAB 3: SYSTEM INTERNAL ---
with tab3:
    st.header("⚙️ เจาะลึกกลยุทธ์ Quant")
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("""
        **🔍 เงื่อนไขการสแกน (Logic)**
        1. **Trend:** ราคา > SMA 200 (ขาขึ้นเท่านั้น)
        2. **Momentum:** RSI < 45 (จุดย่อตัว Buy on Dip)
        3. **Volume:** วอลลุ่มวันนี้ > ค่าเฉลี่ย 5 วัน (มีแรงซื้อจริง)
        """)
    with col_b:
        st.success("""
        **✅ Position Sizing Formula**
        `จำนวนหุ้น = (เงินต้น * %ความเสี่ยง) / (ราคาซื้อ - ราคา ATR Stop Loss)`
        """)

# --- TAB 1: MAIN SCANNER ---
with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + ATR")

    # --- 3. Sidebar: Settings ---
    st.sidebar.header("💰 Portfolio Settings")
    p_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    atr_mult = st.sidebar.slider("ATR Multiplier (ความกว้าง SL):", 1.0, 3.0, 1.5)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกจากลิสต์:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นเอง (เช่น AOT.BK):").upper().strip()

    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    # --- 4. DATA ENGINE ---
    def get_market_data(ticker):
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # Indicators
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            
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
            
            # SL/TP
            df['SL_ATR'] = df['Close'] - (df['ATR'] * atr_mult)
            df['TP_ATR'] = df['Close'] + (df['ATR'] * (atr_mult * 2))
            return df
        except: return None

    # --- 5. PROCESSING ---
    results = []
    if final_list:
        with st.spinner('กำลังประมวลผล...'):
            for t in final_list:
                data = get_market_data(t)
                if data is not None:
                    l = data.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    if p > s and r < 45 and v > va: sig = "🟢 BUY"
                    elif r > 75: sig = "💰 PROFIT"
                    elif p < s: sig = "🔴 EXIT"
                    else: sig = "⚪ WAIT"
                    
                    # Risk Calc
                    risk_amt = p_size * (risk_pct / 100)
                    dist = p - l['SL_ATR']
                    qty = int(risk_amt / dist) if dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": sig, "Vol OK": "✅" if v > va else "❌",
                        "Qty": qty, "SL (ATR)": round(l['SL_ATR'],2), "TP": round(l['TP_ATR'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # --- 6. CHART & PLAN ---
            c1, c2 = st.columns([0.6, 0.4])
            with c1:
                sel = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", res_df['Ticker'])
                df_plot = get_market_data(sel)
                if df_plot is not None:
                    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
                    # Price
                    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df
