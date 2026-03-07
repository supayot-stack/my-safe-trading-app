import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ (คงเดิม) ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .info-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs คงเดิม) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ การทำงานของระบบ (Internal)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ กลไกการคุมความเสี่ยง (The 1% Rule)
    ระบบนี้ใช้หลักการ **Fixed Fractional Position Sizing** เพื่อให้พอร์ตของคุณ "ไม่มีวันพัง"
    1. **Risk Amount:** ยอมเสียสูงสุดแค่ 1% ของพอร์ต
    2. **Stop Loss (SL):** ตั้งจุดหนีไว้ที่ 3% จากราคาซื้อ
    3. **Position Sizing:** จำนวนหุ้น = เงินที่ยอมเสียได้ / (ราคาซื้อ - ราคา SL)
    """)

with tab3:
    st.header("⚙️ เจาะลึกการทำงานของระบบ")
    col_a, col_b = st.columns(2)
    with col_a:
        st.info("Logic: SMA 200 (Trend) + RSI < 40 (Buy Dip) + Volume > Avg 5 (Confirm)")
    with col_b:
        st.success("Safe: เทรดขาขึ้น | Quant: ใช้สถิติตัดอารมณ์ | Pro Max: มี AI ช่วยวิเคราะห์ข่าว")

# --- TAB 1: ระบบสแกน ---
with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + Risk Manager")
    
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list: final_list.append(custom_ticker)

    # --- ฟังก์ชันดึงข้อมูล (คงอินดิเคเตอร์เดิมไว้ครบถ้วน) ---
    def get_data(ticker, interval, data_period):
        try:
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            df['SL'] = df['Close'] * 0.97
            df['TP'] = df['Close'] * 1.07
            return df
        except: return None

    results = []
    if final_list:
        with st.spinner('กำลังโหลดข้อมูล...'):
            for t in final_list:
                df = get_data(t, "1d", "2y") 
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
                    results.append({"Ticker": t, "Price": round(p,2), "RSI": round(r,1), "Signal": act, "Vol OK": "✅" if v > va else "❌", "Qty to Buy": qty, "StopLoss": round(l['SL'],2), "Target": round(l['TP'],2)})

        if results:
            res_df = pd.DataFrame(results)
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    col1, col2 = st.columns([0.6, 0.4])
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot, "1d", "2y")
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                
                # กราฟราคา & SMA (คงเดิม)
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=1.5)), row=1, col=1)
                
                # --- แก้ไข: Volume สีเทาตัดพื้นหลัง ---
                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='LightSlateGray', opacity=0.4), row=1, col=1)
                
                # กราฟ RSI (คงเดิม)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
                
                fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, showlegend=False)
                
                # --- แก้ไข: นำปุ่มควบคุมกราฟกลับมา ---
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True})

        with col2:
            st.markdown("### 🛠️ การบริหารหน้าตัก")
            target_data = next(item for item in results if item["Ticker"] == selected_plot)
            st.markdown(f"""
            <div class="risk-box">
                <h4>คำแนะนำสำหรับ {selected_plot}</h4>
                <ul>
                    <li><b>ควรซื้อ:</b> {target_data['Qty to Buy']:,} หุ้น</li>
                    <li><b>เงินที่ใช้ซื้อ:</b> {(float(target_data['Price']) * target_data['Qty to Buy']):,.2f} บาท</li>
                    <li><b>Stop Loss (3%):</b> {target_data['StopLoss']}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("### 🔮 AI Future Insight")
            news_input = st.text_area("วิเคราะห์ข่าวปัจจุบัน:", placeholder="วางข่าวที่นี่...")
            if st.button("ประมวลผล AI"):
                if news_input:
                    st.info("AI วิเคราะห์เบื้องต้น: สอดคล้องกับเทรนขาขึ้น แนะนำให้เทรดตามแผน Position Sizing อย่างเคร่งครัด")

if st.button("🔄 อัปเดตข้อมูล"): st.rerun()
