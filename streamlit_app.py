import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max v2", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .info-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    .stMetric { background-color: #1e222d; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันหลัก (Logic & Data) ---

@st.cache_data(ttl=3600) # เก็บข้อมูลไว้ 1 ชม. ลดการโหลดซ้ำ
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        # จัดการชื่อหุ้นไทยอัตโนมัติ
        thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB", "BDMS", "GULF"]
        if ticker in thai_tickers and "." not in ticker: ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        
        # ปรับแก้ปัญหา Multi-index ใน pandas version ใหม่
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # --- Technical Indicators ---
        # 1. Trend: SMA 200
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # 2. Momentum: RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        # 3. Volatility: ATR (สำหรับ Dynamic Stop Loss)
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['ATR'] = ranges.max(axis=1).rolling(14).mean()
        
        # 4. Volume Check
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        
        # 5. Risk Management Levels (ATR Based)
        df['SL_Price'] = df['Close'] - (df['ATR'] * 2) # Stop loss 2 เท่าของ ATR
        df['TP_Price'] = df['Close'] + (df['ATR'] * 4) # Target Profit 4 เท่า (R:R 1:2)
        
        return df
    except Exception as e:
        return None

def run_backtest(df):
    """จำลองการซื้อขายย้อนหลังตามกลยุทธ์"""
    bt_df = df.copy()
    # Buy: RSI < 40 + ราคาเหนือ SMA200 (ย่อในขาขึ้น)
    bt_df['Signal'] = np.where((bt_df['RSI'] < 40) & (bt_df['Close'] > bt_df['SMA200']), 1, 0)
    # Sell: RSI > 70 หรือ ราคาหลุด SMA200
    bt_df.loc[(bt_df['RSI'] > 70) | (bt_df['Close'] < bt_df['SMA200']), 'Signal'] = -1
    
    bt_df['Position'] = bt_df['Signal'].replace(0, method='ffill').shift(1)
    bt_df['Daily_Return'] = bt_df['Close'].pct_change()
    bt_df['Strategy_Return'] = bt_df['Daily_Return'] * bt_df['Position'].fillna(0)
    bt_df['Cum_Return'] = (1 + bt_df['Strategy_Return']).cumprod() - 1
    return bt_df

# --- 3. ส่วน UI ---

tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & Backtest", "📖 คู่มือความเสี่ยง (ATR)", "⚙️ ระบบภายใน"])

with tab2:
    st.header("🛡️ กลยุทธ์ ATR Dynamic Stop Loss")
    st.markdown("""
    ### ทำไมต้องใช้ ATR?
    แทนที่จะใช้ % ตายตัว (เช่น 3%) ระบบนี้ใช้ **ATR (Average True Range)** เพื่อวัดความผันผวนจริงของหุ้น
    - **หุ้นผันผวนสูง:** SL จะกว้างขึ้นเพื่อป้องกันโดนสะบัดหลุด (Stop hunt)
    - **หุ้นผันผวนต่ำ:** SL จะแคบลงเพื่อให้ Position Size ใหญ่ขึ้นได้
    
    > **สูตรการคำนวณ:** `จำนวนหุ้น = เงินที่ยอมเสียได้ / (2 x ATR)`
    """)
    

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + Backtester")
    
    # Sidebar: Settings
    st.sidebar.header("💰 Portfolio & Risk")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (% ของพอร์ต):", 0.1, 5.0, 1.0)
    
    st.sidebar.divider()
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "PTT.BK", "CPALL.BK"]
    selected_assets = st.sidebar.multiselect("Asset Watchlist:", options=default_assets, default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ (e.g. GOOGL, PTT.BK):").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list: final_list.append(custom_ticker)

    # ประมวลผลภาพรวม
    results = []
    if final_list:
        with st.spinner('Scanning the Market...'):
            for t in final_list:
                df = get_data(t)
                if df is not None:
                    last = df.iloc[-1]
                    # Signal Logic
                    if last['Close'] > last['SMA200'] and last['RSI'] < 40: 
                        status = "🟢 STRONG BUY"
                    elif last['RSI'] > 75: 
                        status = "💰 TAKE PROFIT"
                    elif last['Close'] < last['SMA200']: 
                        status = "🔴 AVOID/EXIT"
                    else: 
                        status = "⚪ WAIT"
                    
                    risk_amt = portfolio_size * (risk_per_trade / 100)
                    sl_dist = last['Close'] - last['SL_Price']
                    qty = int(risk_amt / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(last['Close'],2), 
                        "RSI": round(last['RSI'],1), "Signal": status,
                        "Qty": qty, "ATR SL": round(last['SL_Price'],2),
                        "Target": round(last['TP_Price'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            st.subheader("🎯 สรุปสัญญาณและแผนการเทรด")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # วิเคราะห์รายตัว & Backtest
    if results:
        col1, col2 = st.columns([0.65, 0.35])
        selected_plot = col1.selectbox("🔍 เลือกตัวเพื่อดู Backtest และ กราฟเทคนิค:", [r['Ticker'] for r in results])
        
        df_full = get_data(selected_plot)
        df_bt = run_backtest(df_full)
        
        with col1:
            # กราฟราคา
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_full.index, open=df_full['Open'], high=df_full['High'], low=df_full['Low'], close=df_full['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_full.index, y=df_full['SMA200'], name='Trend (SMA200)', line=dict(color='yellow')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_full.index, y=df_full['RSI'], name='Momentum (RSI)', line=dict(color='cyan')), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
            fig.update_layout(height=5
