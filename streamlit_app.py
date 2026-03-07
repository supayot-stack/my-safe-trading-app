import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTINGS ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; color: #ffffff; }
.risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
.info-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. CORE FUNCTIONS ---
def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_cp = np.abs(df['High'] - df['Close'].shift())
    low_cp = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def get_data(ticker, interval="1d", data_period="2y"):
    try:
        # Auto-adjust Thai tickers
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        symbol = f"{ticker}.BK" if ticker in thai_list else ticker
        
        df = yf.download(symbol, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Calculate Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        df['ATR'] = calculate_atr(df)
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        df['TP'] = df['Close'] + (df['ATR'] * 5)
        return df
    except: return None

# --- 3. UI LAYOUT ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน", "📖 คู่มือบริหารความเสี่ยง", "⚙️ ระบบหลังบ้าน"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    st.sidebar.header("💰 Portfolio")
    port_size = st.sidebar.number_input("เงินลงทุนทั้งหมด (บาท):", min_value=1000, value=100000)
    risk_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.1, 5.0, 1.0)
    
    st.sidebar.divider()
    assets = ["NVDA", "AAPL", "BTC-USD", "PTT.BK", "CPALL.BK"]
    selected = st.sidebar.multiselect("เลือกหุ้น:", options=assets + ["TSLA", "GOOGL", "ETH-USD"], default=assets)
    custom = st.sidebar.text_input("➕ เพิ่ม Ticker อื่นๆ:").upper().strip()
    
    final_list = list(selected)
    if custom and custom not in final_list: final_list.append(custom)

    results = []
    if final_list:
        with st.spinner('Calculating...'):
            for t in final_list:
                df = get_data(t)
                if df is not None and len(df) > 20:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    if p > s and r < 45 and v > va: signal = "🟢 STRONG BUY"
                    elif r > 70: signal = "💰 TAKE PROFIT"
                    elif p < s: signal = "🔴 EXIT/AVOID"
                    else: signal = "⚪ WAIT"
                        
                    risk_money = port_size * (risk_pct / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_money / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p, 2), "RSI": round(r, 1),
                        "Signal": signal, "Qty": qty, "SL": round(l['SL'], 2), "Target": round(l['TP'], 2)
                    })

        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            st.divider()
            
            col1, col2 = st.columns([0.6, 0.4])
            with col1:
                pick = st.selectbox("วิเคราะห์กราฟ:", [r['Ticker'] for r in results])
                pdf = get_data(pick)
                if pdf is not None:
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
                    fig.add_trace(go.Candlestick(x=pdf.index, open=pdf['Open'], high=pdf['High'], low=pdf['Low'], close=pdf['Close'], name="Price"), 1, 1)
                    fig.add_trace(go.Scatter(x=pdf.index, y=pdf['SMA200'], name="SMA200", line=dict(color='yellow')), 1, 1)
                    fig.add_trace(go.Scatter(x=pdf.index, y=pdf['RSI'], name="RSI", line=dict(color='cyan')), 2, 1)
                    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                pd_data = next(i for i in results if i['Ticker'] == pick)
                st.markdown(f"""
                <div class="risk-box">
                    <h4>{pick} Strategy</h4>
                    <p>คำแนะนำ: <b>{pd_data['Signal']}</b></p>
                    <hr>
                    <li>จำนวนที่ควรซื้อ: <b>{pd_data['Qty']:,}</b></li>
                    <li>จุดตัดขาดทุน (ATR): <b>{pd_data['SL']}</b></li>
                    <li>กำไรเป้าหมาย: <b>{pd_data['Target']}</b></li>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    หลักการ **Fixed Fractional Position Sizing** ช่วยให้พอร์ตไม่พัง:
    1. **Risk Per Trade:** เสียได้ไม่เกิน 1% ของพอร์ตต่อไม้
    2. **ATR SL:** ใช้ความผันผวนจริงกำหนดจุดถอย
    """)
    

with tab3:
    st.write("สถานะ: ออนไลน์")
