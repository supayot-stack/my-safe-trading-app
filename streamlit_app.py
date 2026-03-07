import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 20px; border-radius: 12px; border-left: 6px solid #00ffcc; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & ATR", "📖 คู่มือเทคนิค"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + ATR")

    # --- 3. Sidebar ---
    st.sidebar.header("💰 Portfolio Settings")
    p_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    atr_mult = st.sidebar.slider("ATR Multiplier (SL):", 1.0, 3.0, 1.5)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกจากลิสต์:", options=list(set(default_assets + ["PTT.BK", "CPALL.BK"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นเอง:").upper().strip()

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
            
            # ATR Calculation
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            df['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR'] = df['TR'].rolling(14).mean()
            
            # Stop Loss & Target
            df['SL'] = df['Close'] - (df['ATR'] * atr_mult)
            df['TP'] = df['Close'] + (df['ATR'] * (atr_mult * 2))
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
                    
                    sig = "⚪ WAIT"
                    if p > s and r < 45 and v > va: sig = "🟢 BUY"
                    elif r > 75: sig = "💰 PROFIT"
                    elif p < s: sig = "🔴 EXIT"
                    
                    risk_amt = p_size * (risk_pct / 100)
                    dist = p - l['SL']
                    qty = int(risk_amt / dist) if dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": sig, "Vol OK": "✅" if v > va else "❌",
                        "Qty": qty, "SL": round(l['SL'],2), "TP": round(l['TP'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            
            # --- 6. CHART & PLAN ---
            st.divider()
            c1, c2 = st.columns([0.6, 0.4])
            with c1:
                sel = st.selectbox("🔍 เลือกหุ้นเพื่อดูแผนเทรด:", res_df['Ticker'])
                df_p = get_market_data(sel)
                if df_p is not None:
                    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                        vertical_spacing=0.05, row_heights=[0.5, 0.25,
