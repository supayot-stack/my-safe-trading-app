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
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือเทคนิค"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")

    # --- 3. Sidebar ---
    st.sidebar.header("💰 Portfolio Settings")
    p_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000)
    r_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=list(set(default_assets + ["PTT.BK", "CPALL.BK"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นเอง:").upper().strip()

    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    # --- 4. DATA ENGINE ---
    def get_data(ticker):
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            
            df['SL'] = df['Close'] * 0.97
            df['TP'] = df['Close'] * 1.07
            return df
        except: return None

    # --- 5. PROCESSING ---
    results = []
    if final_list:
        with st.spinner('กำลังโหลดข้อมูล...'):
            for t in final_list:
                df = get_data(t)
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    if p > s and r < 40 and v > va: sig = "🟢 BUY"
                    elif r > 75: sig = "💰 PROFIT"
                    elif p < s: sig = "🔴 EXIT"
                    else: sig = "⚪ WAIT"
                    
                    risk_amt = p_size * (r_pct / 100)
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
            
            # --- 6. CHART ANALYSIS ---
            st.divider()
            c1, c2 = st.columns([0.6, 0.4])
            with c1:
                sel = st.selectbox("🔍 เลือกหุ้นเพื่อดูกราฟ:", res_df['Ticker'])
                df_p = get_data(sel)
                if df_p is not None:
                    # ปรับ Volume เป็นสีเทา (LightSlateGray) และโปร่งแสง (Opacity 0.4)
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                    
                    # Row 1: Candlestick & SMA & Volume (Overlay)
                    fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA2
