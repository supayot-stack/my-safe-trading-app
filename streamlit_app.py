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
    .info-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ การทำงานของระบบ (Internal)"])

# --- TAB 2: คู่มือบริหารความเสี่ยง ---
with tab2:
    st.header("📖 กฎเหล็ก 1% ของ investor")
    st.markdown("""
    ### 🛡️ กลไกการคุมความเสี่ยง (The 1% Rule)
    ระบบนี้ใช้หลักการ **Fixed Fractional Position Sizing**
    
    1. **Risk Amount:** เงินที่ยอมเสียได้สูงสุด (1% ของพอร์ต) 
    2. **Stop Loss (SL):** ตั้งจุดหนีไว้ที่ 3%
    3. **Position Sizing:** `จำนวนหุ้น = เงินที่ยอมเสีย / (ราคาซื้อ - ราคา SL)`
    """)

# --- TAB 3: การทำงานของระบบ ---
with tab3:
    st.header("⚙️ System Manual")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🔍 Logic Flow")
        st.info("1. SMA 200 Trend | 2. RSI < 40 | 3. Volume > Avg 5 Days")
    with col_b:
        st.subheader("✅ Definition")
        st.markdown("- **Safe:** ขาขึ้นเท่านั้น | **Quant:** สถิติ 100%")

# --- TAB 1: ระบบหลัก ---
with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด:", min_value=1000, value=100000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยง (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.header("🔍 Assets")
    selected_assets = st.sidebar.multiselect("เลือกหุ้น:", ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK", "PTT.BK"], default=["NVDA", "AAPL"])
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้น:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker: final_list.append(custom_ticker)

    def get_data(ticker, interval, data_period):
        try:
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            df['SL'] = df['Close'] * 0.97
            return df
        except: return None

    results = []
    for t in final_list:
        df = get_data(t, "1d", "2y")
        if df is not None:
            l = df.iloc[-1]
            act = "🟢 BUY" if l['Close'] > l['SMA200'] and l['RSI'] < 40 else "⚪ Wait"
            risk_amt = portfolio_size * (risk_per_trade / 100)
            qty = int(risk_amt / (l['Close'] - l['SL'])) if (l['Close'] - l['SL']) > 0 else 0
            results.append({"Ticker": t, "Price": round(l['Close'],2), "Signal": act, "Qty": qty, "SL": round(l['SL'],2)})

    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True)
        st.divider()
        
        col1, col2 = st.columns([0.6, 0.4])
        with col1:
            sel = st.selectbox("เลือกหุ้นดูรายละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(sel, "
