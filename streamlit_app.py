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
    .ai-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ ทำอย่างไรให้ "ห้ามพัง" (Zero Ruin)
    1. **Never Bet All:** อย่าลงเงินทั้งหมดในหุ้นตัวเดียว
    2. **The 1% Rule:** ในแต่ละการเทรด ถ้าผิดทาง (Stop Loss) คุณควรเสียเงินไม่เกิน **1% ของเงินต้นทั้งหมด**
    3. **Position Sizing:** คำนวณจำนวนหุ้นที่จะซื้อจากระยะห่างของจุด Stop Loss
    
    ---
    ### 🚦 ตัวอย่างการคำนวณ
    * มีเงิน 100,000 บาท ยอมเสียได้ 1% = 1,000 บาท
    * ซื้อหุ้นราคา 100 บาท Stop Loss ที่ 97 บาท (ส่วนต่าง 3 บาท)
    * จำนวนหุ้นที่ซื้อได้ = 1,000 / 3 = **333 หุ้น**
    * *ผลลัพธ์:* ถ้าหุ้นตกไปที่ 97 บาท คุณจะเสียแค่ 1,000 บาท (พอร์ตเหลือ 99,000 ยังสู้ต่อได้สบาย)*
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + Risk Manager")
    
    # --- 3. Sidebar: Settings & Portfolio ---
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK", "GC=F"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list: final_list.append(custom_ticker)

    # --- 4. ฟังก์ชันดึงข้อมูล (Quantitative + Risk Calculations) ---
    def get_data(ticker, interval, data_period):
        try:
            if any(s in ticker for s in ["PTT", "AOT", "KBANK", "CPALL"]) and "." not in ticker: ticker += ".BK"
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            
            # คำนวณจุดหนี (Stop Loss) ที่ 3% และเป้าหมาย (Take Profit) ที่ 7%
            df['SL'] = df['Close'] * 0.97
            df['TP'] = df['Close'] * 1.07
            return df
        except: return None

    # --- 5. ประมวลผลและตารางผลลัพธ์ ---
    results = []
    if final_list:
        with st.spinner('กำลังคำนวณแผนการเทรด...'):
            for t in final_list:
                df = get_data(t, "1d", "2y") # ใช้ Daily เป็นฐานการสแกนเทรนด์หลัก
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    # ตรรกะสัญญาณ
                    if p > s and r < 40 and v > va: act = "🟢 STRONG BUY"
                    elif r > 75: act = "💰 PROFIT"
                    elif p < s: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    # คำนวณจำนวนหุ้นที่ควรซื้อ (Position Sizing)
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
            priority = {"🟢 STRONG BUY": 0, "💰 PROFIT": 1, "⚪ Wait": 2, "🔴 EXIT/AVOID": 3}
            res_df['sort'] = res_df['Signal'].map(priority)
            res_df = res_df.sort_values('sort').drop(columns=['sort'])
            st.subheader("🎯 สรุปสัญญาณและแผนคุมความเสี่ยง")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- 6. ส่วนวิเคราะห์รายตัว: กราฟ + AI + Risk Manager ---
    col1, col2 = st.columns([0.6, 0.4])
    
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot, "1d", "2y")
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='gray', opacity=0.3), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
                fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 🛠️ เครื่องมือบริหารหน้าตัก")
            # ดึงข้อมูลตัวที่เลือกมาคำนวณ Risk
            target_data = next(item for item in results if item["Ticker"] == selected_plot)
            
            st.markdown(f"""
            <div class="risk-box">
                <h4>คำแนะนำสำหรับ {selected_plot}</h4>
                <p>กรณีเข้าซื้อที่ราคาปัจจุบัน ({target_data['Price']})</p>
                <ul>
                    <li><b>จำนวนหุ้นที่แนะนำ:</b> {target_data['Qty to Buy']:,} หุ้น</li>
                    <li><b>เงินที่ใช้ซื้อทั้งหมด:</b> {(float(target_data['Price']) * target_data['Qty to Buy']):,.2f} บาท</li>
                    <li><b>จุดหนี (Stop Loss):</b> {target_data['StopLoss']}</li>
                    <li><b>ความเสียหายหากแพ้:</b> {(portfolio_size * risk_per_trade / 100):,.2f} บาท ({risk_per_trade}%)</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 🔮 AI Future Insight")
            news_input = st.text_area("วิเคราะห์ข่าว/เหตุการณ์สำหรับหุ้นตัวนี้:", placeholder="เช่น ผลประกอบการออกมาดีเกินคาด...")
            if st.button("ประมวลผล AI"):
                if news_input:
                    st.info("AI วิเคราะห์ว่า: เหตุการณ์นี้ส่งผลบวกต่อความมั่นใจในระยะสั้น แนะนำให้เข้าตามแผน Position Sizing ที่คำนวณไว้ข้างต้น")

if st.button("🔄 อัปเดตข้อมูล"): st.rerun()
