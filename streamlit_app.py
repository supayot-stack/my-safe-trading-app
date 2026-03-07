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

# --- 2. ฟังก์ชันดึงข้อมูล ---
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        symbol = f"{ticker}.BK" if ticker in thai_list and "." not in ticker else ticker
        
        df = yf.download(symbol, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if len(df) < 200: return None
        
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        df['SL'] = df['Close'] * 0.97
        df['TP'] = df['Close'] * 1.07
        return df
    except:
        return None

# --- 3. ส่วนเมนู (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ ระบบหลังบ้าน"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    default_assets = ["NVDA", "AAPL", "BTC-USD", "PTT.BK", "CPALL.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=default_assets + ["TSLA", "GOOGL", "SET50.BK"], default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    results = []
    if final_list:
        with st.spinner('กำลังประมวลผล...'):
            for t in final_list:
                df = get_data(t)
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    if p > s and r < 40 and v > va: act = "🟢 STRONG BUY"
                    elif r > 75: act = "💰 PROFIT"
                    elif p < s: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    risk_amount = portfolio_size * (risk_per_trade / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_amount / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p, 2), "RSI": round(r, 1),
                        "Signal": act, "Qty to Buy": qty, "StopLoss": round(l['SL'], 2)
                    })

        if results:
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
            
            st.divider()
            col1, col2 = st.columns([0.6, 0.4])
            with col1:
                pick = st.selectbox("วิเคราะห์กราฟ:", [r['Ticker'] for r in results])
                pdf = get_data(pick)
                if pdf is not None:
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                    fig.add_trace(go.Candlestick(x=pdf.index, open=pdf['Open'], high=pdf['High'], low=pdf['Low'], close=pdf['Close'], name='Price'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=pdf.index, y=pdf['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
                    fig.add_trace(go.Scatter(x=pdf.index, y=pdf['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
                    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                target = next(i for i in results if i['Ticker'] == pick)
                st.markdown(f"""
                <div class="risk-box">
                    <h4>{pick} Strategy</h4>
                    <p>คำแนะนำ: <b>{target['Signal']}</b></p>
                    <hr>
                    <li>ซื้อจำนวน: <b>{target['Qty to Buy']:,}</b> หุ้น</li>
                    <li>จุดหนี (SL): <b>{target['StopLoss']}</b></li>
                    <li>เงินที่เสี่ยง: <b>{(portfolio_size * risk_per_trade / 100):,.2f}</b></li>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    หลักการนี้ช่วยให้พอร์ตของคุณไม่มีวันพัง (Zero Ruin) ต่อให้ทายผิดหลายครั้ง
    1. **Risk per Trade:** เสียได้ไม่เกิน 1% ของพอร์ตต่อไม้
    2. **Position Sizing:** ซื้อหุ้นตามระยะห่างของจุด Stop Loss
    """)
    

with tab3:
    st.write("สถานะระบบ: ออนไลน์")
    if st.button("🔄 อัปเดตข้อมูล"): st.rerun()
